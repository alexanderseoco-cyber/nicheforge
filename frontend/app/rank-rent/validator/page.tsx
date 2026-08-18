"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AppShell } from "../../components/AppShell";
import "./validator.css";

const API = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000/api/v1";
const stages = ["Population", "Search Volume", "SERP", "DA Gate", "Deep Analysis", "KD", "Result"];
const profile = { min_population: 20000, max_population: 120000, min_search_volume: 260, da_threshold: 10, required_low_da_count: 4, ideal_weak_domains: 5, organic_depth: 10, kd_enabled: true, kd_provider: "moz", kd_threshold: 15, kd_mode: "PRIORITY" };
type Handoff = { handoff_id: string; evidence_id: string; keyword: string; search_volume: number | null; provider: string; country_code: string; status: string; validation_scope?: string; location_status?: string; population_applicability?: string; serp_mode?: string; readiness_status?: string };
type AttachOutcome = { handoff_id: string; keyword?: string; status: string; validation_scope?: string; project_candidate_id?: string; city_candidates?: LocationCandidate[]; authority_opportunity?: string; authority_opportunity_reason?: string; weak_site_count?: number; authority_threshold?: number };
type AuthorityRecord = { position: number; domain?: string; url?: string; da?: number | null; pa?: number | null; ahrefs_dr?: number | null; referring_domains?: number | null; referring_main_domains?: number | null; referring_ips?: number | null; referring_subnets?: number | null; backlinks?: number | null; backlinks_spam_score?: number | null; provider?: string | null; da_provider?: string | null; dr_provider?: string | null; backlink_provider?: string | null };
type Run = { id: string; project_id: string; status: string; counters: Record<string, unknown>; progress?: number; candidate_results?: Array<{ keyword?: string; validation_scope?: string; population_applicability?: string; serp_mode?: string; serp_provider?: string | null; serp_target?: string | null; serp_fetched_at?: string | null; serp_snapshot_id?: string | null; serp_evidence_state?: string | null; serp_requested_depth?: number | null; serp_observed_depth?: number | null; serp_coverage_ratio?: number | null; serp_provider_status_code?: number | null; serp_provider_status_message?: string | null; authority_opportunity?: string | null; authority_opportunity_reason?: string | null; weak_site_count?: number | null; authority_threshold?: number | null; status: string; reason_codes: string[]; population: string; search_volume: string; search_volume_value?: number | null; search_volume_provider?: string | null; serp: string; serp_reason?: string | null; serp_count?: number; serp_required?: number; serp_evidence?: Array<{ position: number; domain: string; url: string; title?: string }>; da: string; da_evidence?: AuthorityRecord[]; deep_analysis: string; kd: string; final_result: string }> };
type InitState = "idle" | "setting_up_project" | "attaching_candidate" | "previewing" | "ready" | "location_confirmation_required" | "initialization_error";
type LocationCandidate = { city: string; state: string; city_id: string };
type ActiveRunContext = { run_id: string; handoff_ids: string[]; evidence_ids: string[]; keywords: string[]; project_id: string; project_candidate_ids: string[] };
class ApiError extends Error { detail: unknown; constructor(detail: unknown) { super(typeof detail === "string" ? detail : "NicheForge request failed"); this.detail = detail; } }

function runStorageKey(handoffIds: string[]) {
  return `nicheforge_active_run_id:${[...handoffIds].sort().join(",")}`;
}

function readActiveRunContext(handoffList: Handoff[]): ActiveRunContext | null {
  if (!handoffList.length) return null;
  try {
    const raw = sessionStorage.getItem(runStorageKey(handoffList.map(item => item.handoff_id)));
    if (!raw) return null;
    const value = JSON.parse(raw) as ActiveRunContext;
    const ids = handoffList.map(item => item.handoff_id).sort();
    const evidence = handoffList.map(item => item.evidence_id).sort();
    const keywords = handoffList.map(item => item.keyword.trim().toLowerCase()).sort();
    if (!value?.run_id || value.project_id === undefined || JSON.stringify(value.handoff_ids?.slice().sort()) !== JSON.stringify(ids) || JSON.stringify(value.evidence_ids?.slice().sort()) !== JSON.stringify(evidence) || JSON.stringify(value.keywords?.map(item => item.trim().toLowerCase()).sort()) !== JSON.stringify(keywords)) return null;
    return value;
  } catch { return null; }
}

function runMatchesHandoffs(value: Run, handoffList: Handoff[], expectedProjectId?: string) {
  if (expectedProjectId && value.project_id && value.project_id !== expectedProjectId) return false;
  const expected = handoffList.map(item => item.keyword.trim().toLowerCase()).sort();
  const actual = (value.candidate_results || []).map(item => item.keyword?.trim().toLowerCase()).filter((item): item is string => !!item).sort();
  return actual.length > 0 && expected.length === actual.length && expected.every((keyword, index) => keyword === actual[index]);
}

function headers(): Record<string, string> {
  const token = sessionStorage.getItem("nicheforge_access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(path: string, init?: RequestInit, timeoutMs = 15000) {
  const controller = new AbortController();
  const timeout = timeoutMs > 0 ? window.setTimeout(() => controller.abort(), timeoutMs) : undefined;
  const response = await fetch(`${API}${path}`, { ...init, signal: controller.signal, headers: { "Content-Type": "application/json", ...headers(), ...(init?.headers || {}) } }).finally(() => window.clearTimeout(timeout));
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(data.detail || "NicheForge request failed");
  return data;
}

async function pollRun(runId: string, onUpdate: (value: Run) => void) {
  for (let attempt = 0; attempt < 90; attempt += 1) {
    const current = await request(`/runs/${encodeURIComponent(runId)}`) as Run;
    onUpdate(current);
    if (!["CREATED", "RUNNING"].includes(current.status)) return current;
    await new Promise(resolve => window.setTimeout(resolve, 1500));
  }
  throw new Error("Validation is still running. Refresh later to load the existing run.");
}

export default function Validator() {
  return <Suspense fallback={<div className="card card-body">Loading Validator…</div>}><ValidatorClient /></Suspense>;
}

function ValidatorClient() {
  const params = useSearchParams();
  const handoffId = params.get("handoff_id") || params.get("handoff");
  const explicitProjectId = params.get("project_id");
  const [handoffs, setHandoffs] = useState<Handoff[]>([]);
  const [selected, setSelected] = useState<Handoff | null>(null);
  const [project, setProject] = useState("");
  const [projectId, setProjectId] = useState("");
  const [candidateCount, setCandidateCount] = useState(0);
  const [attached, setAttached] = useState(false);
  const [run, setRun] = useState<Run | null>(null);
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [errorKind, setErrorKind] = useState("");
  const [initializationFailed, setInitializationFailed] = useState(false);
  const [initState, setInitState] = useState<InitState>("idle");
  const [locationCandidates, setLocationCandidates] = useState<LocationCandidate[]>([]);
  const [locationAmbiguities, setLocationAmbiguities] = useState<Array<{ handoff_id: string; keyword: string; candidates: LocationCandidate[] }>>([]);
  const [selectedLocations, setSelectedLocations] = useState<Record<string, LocationCandidate>>({});
  const [attachOutcomes, setAttachOutcomes] = useState<AttachOutcome[]>([]);
  const initializationStarted = useRef(false);

  useEffect(() => {
    initializationStarted.current = false;
    setHandoffs([]); setSelected(null); setRun(null); setPreview(null); setAttachOutcomes([]);
    setProjectId(""); setCandidateCount(0); setAttached(false); setLocationAmbiguities([]); setLocationCandidates([]);
    setError(""); setErrorKind(""); setInitializationFailed(false); setInitState("idle");
  }, [handoffId, explicitProjectId]);

  useEffect(() => {
    const storedIds = !handoffId ? (() => { try { const value = JSON.parse(sessionStorage.getItem("nicheforge_last_handoff_ids") || "[]"); return Array.isArray(value) ? value.filter((id): id is string => typeof id === "string" && !!id) : []; } catch { return []; } })() : [];
    const ids = handoffId ? [handoffId] : storedIds;
    const paths = ids.length ? ids.map(id => `/rank-rent/handoffs/${encodeURIComponent(id)}`) : ["/rank-rent/handoffs"];
    Promise.all(paths.map(path => fetch(`${API}${path}`, { headers: headers() }).then(async response => { if (!response.ok) throw new Error(); return response.json(); })))
      .then(values => { const list = values.flatMap(value => Array.isArray(value) ? value : [value]) as Handoff[]; setHandoffs(list); setSelected(list[0] || null); if (storedIds.length) sessionStorage.removeItem("nicheforge_last_handoff_ids"); })
      .catch(() => { if (handoffId) showError("The requested Search Volume handoff could not be found.", "API ERROR"); });
  }, [handoffId, explicitProjectId]);

  useEffect(() => {
    if (!handoffs.length || initializationStarted.current) return;
    initializationStarted.current = true;
    // Never restore the pre-namespace global key. It can belong to another keyword.
    sessionStorage.removeItem("nicheforge_active_run_id");
    const stored = readActiveRunContext(handoffs);
    if (stored) {
      void pollRun(stored.run_id, value => {
        if (!runMatchesHandoffs(value, handoffs, stored.project_id)) throw new Error("Stored validation run does not belong to the current handoff.");
        setRun(value);
        if (value.project_id) { setProjectId(value.project_id); sessionStorage.setItem("nicheforge_current_project_id", value.project_id); }
        setCandidateCount(value.candidate_results?.length || 0);
        setAttached(true);
        setInitState("ready");
      }).catch(() => { sessionStorage.removeItem(runStorageKey(handoffs.map(item => item.handoff_id))); initializationStarted.current = false; void initialize(handoffs); });
      return;
    }
    sessionStorage.removeItem(runStorageKey(handoffs.map(item => item.handoff_id)));
    void initialize(handoffs);
  }, [handoffs]);

  const progress = useMemo(() => {
    if (!run) return 0;
    if (typeof run.progress === "number") return run.progress;
    const total = Number(run.counters?.total_selected || run.counters?.total || 0);
    const complete = Number(run.counters?.completed || run.counters?.complete || run.counters?.processed || 0);
    return total ? Math.min(100, Math.round(complete / total * 100)) : run.status === "COMPLETED" ? 100 : 0;
  }, [run]);

  function showError(message: string, kind = "ERROR") { setError(message); setErrorKind(kind); }

  async function initialize(importedHandoffs: Handoff[]) {
    setBusy(true); setError(""); setInitializationFailed(false); setInitState("setting_up_project");
    try {
      // A new Search Volume handoff batch gets an isolated project by default.
      // Reuse is opt-in through an explicit project_id query parameter.
      let resolvedProjectId = explicitProjectId;
      if (resolvedProjectId) {
        try {
          await request(`/projects/${encodeURIComponent(resolvedProjectId)}/validation-preview`, { method: "POST", body: JSON.stringify({ profile, candidate_ids: [] }) });
        } catch (cause) {
          if (cause instanceof Error && /404|not found/i.test(cause.message)) {
            sessionStorage.removeItem("nicheforge_current_project_id");
            resolvedProjectId = null;
          } else if (cause instanceof Error && cause.name === "AbortError") throw cause;
        }
      }
      if (!resolvedProjectId) {
        const created = await request("/projects", { method: "POST", body: JSON.stringify({ name: project || "Rank & Rent Project", profile }) });
        resolvedProjectId = created.id;
      }
      if (!resolvedProjectId) throw new Error("Project creation returned no project ID.");
      const finalProjectId = resolvedProjectId;
      sessionStorage.setItem("nicheforge_current_project_id", finalProjectId);
      setProjectId(finalProjectId);
      setInitState("attaching_candidate");
      const attachedResult = await request(`/projects/${encodeURIComponent(finalProjectId)}/handoffs/attach`, { method: "POST", body: JSON.stringify({ handoff_ids: importedHandoffs.map(item => item.handoff_id) }) });
      const count = Number(attachedResult.created_count || 0) + Number(attachedResult.existing_count || 0);
      setAttachOutcomes((attachedResult.results || []) as AttachOutcome[]);
      const pending = (attachedResult.results || []).filter((item: { status?: string }) => item.status === "LOCAL_LOCATION_REQUIRED");
      if (pending.length && count === 0) {
        setCandidateCount(0); setAttached(false);
        setLocationAmbiguities(pending.map((item: { handoff_id: string; keyword: string; city_candidates?: LocationCandidate[] }) => ({ handoff_id: item.handoff_id, keyword: item.keyword, candidates: item.city_candidates || [] })));
        setInitState("location_confirmation_required"); setError(""); setErrorKind("LOCATION CONFIRMATION REQUIRED");
        return;
      }
      if (count < 1 || !attachedResult.project_candidate_ids?.length) throw new Error("The handoff did not produce an executable ProjectCandidate.");
      setCandidateCount(count); setAttached(true);
      if (pending.length) setLocationAmbiguities(pending.map((item: { handoff_id: string; keyword: string; city_candidates?: LocationCandidate[] }) => ({ handoff_id: item.handoff_id, keyword: item.keyword, candidates: item.city_candidates || [] })));
      setInitState("previewing");
      const previewData = await request(`/projects/${encodeURIComponent(finalProjectId)}/validation-preview`, { method: "POST", body: JSON.stringify({ profile, candidate_ids: attachedResult.project_candidate_ids }) });
      setPreview(previewData); setInitState(pending.length ? "location_confirmation_required" : "ready");
    } catch (cause) {
      if (cause instanceof ApiError && typeof cause.detail === "object" && cause.detail && ["HANDOFF_CITY_AMBIGUOUS", "HANDOFF_CITY_UNRESOLVED"].includes((cause.detail as { code?: string }).code || "") && (((cause.detail as { candidates?: LocationCandidate[] }).candidates || []).length > 0 || ((cause.detail as { ambiguities?: unknown[] }).ambiguities || []).length > 0)) {
        const detail = cause.detail as { candidates?: LocationCandidate[]; ambiguities?: Array<{ handoff_id: string; keyword: string; candidates: LocationCandidate[] }> };
        setLocationCandidates(detail.candidates || []);
        setLocationAmbiguities(detail.ambiguities || (detail.candidates ? [{ handoff_id: handoffs[0]?.handoff_id || "", keyword: handoffs[0]?.keyword || "", candidates: detail.candidates }] : []));
        setInitState("location_confirmation_required");
        setErrorKind("LOCATION CONFIRMATION REQUIRED");
        setError("");
        return;
      }
      setInitializationFailed(true); setInitState("initialization_error");
      const message = cause instanceof ApiError && typeof cause.detail === "object" && cause.detail ? String((cause.detail as { message?: string }).message || cause.message) : cause instanceof DOMException && cause.name === "AbortError" ? "Initialization timed out while waiting for the backend." : cause instanceof Error ? cause.message : "Candidate initialization failed";
      showError(message, "INITIALIZATION ERROR");
    } finally { setBusy(false); }
  }

  async function createProject() {
    if (projectId) return;
    setBusy(true); setError("");
    try {
      const data = await request("/projects", { method: "POST", body: JSON.stringify({ name: project || "Rank & Rent Project", profile }) });
      setProjectId(data.id); sessionStorage.setItem("nicheforge_current_project_id", data.id);
    } catch (cause) { setInitializationFailed(true); setInitState("initialization_error"); showError(cause instanceof Error ? cause.message : "Project creation failed", "INITIALIZATION ERROR"); }
    finally { setBusy(false); }
  }

  async function chooseLocation(handoffId: string, candidate: LocationCandidate) {
    if (!projectId || !handoffs.length) return;
    setBusy(true); setError(""); setLocationCandidates([]); setInitState("attaching_candidate");
    try {
      const nextLocations = { ...selectedLocations, [handoffId]: candidate };
      setSelectedLocations(nextLocations);
      const data = await request(`/projects/${encodeURIComponent(projectId)}/handoffs/attach`, { method: "POST", body: JSON.stringify({ handoff_ids: handoffs.map(item => item.handoff_id), location_overrides: Object.fromEntries(Object.entries(nextLocations).map(([id, value]) => [id, { city: value.city, state_code: value.state, city_id: value.city_id }])) }) });
      const count = Number(data.created_count || 0) + Number(data.existing_count || 0);
      setCandidateCount(count); setAttached(count > 0); setLocationAmbiguities([]); setInitState("previewing");
      const matched = (data.results || []).find((item: { handoff_id?: string }) => item.handoff_id === handoffId);
      setAttachOutcomes(items => items.map(item => item.handoff_id === handoffId ? { ...item, status: matched?.status || "LOCAL_READY", project_candidate_id: matched?.project_candidate_id } : item));
      setPreview(await request(`/projects/${encodeURIComponent(projectId)}/validation-preview`, { method: "POST", body: JSON.stringify({ profile, candidate_ids: data.project_candidate_ids }) }));
      setInitState("ready");
    } catch (cause) {
      if (cause instanceof ApiError && typeof cause.detail === "object" && cause.detail && ["HANDOFF_CITY_AMBIGUOUS", "HANDOFF_CITY_UNRESOLVED"].includes((cause.detail as { code?: string }).code || "") && (((cause.detail as { candidates?: LocationCandidate[] }).candidates || []).length > 0 || ((cause.detail as { ambiguities?: unknown[] }).ambiguities || []).length > 0)) {
        const detail = cause.detail as { handoff_id?: string; keyword?: string; candidates?: LocationCandidate[]; ambiguities?: Array<{ handoff_id: string; keyword: string; candidates: LocationCandidate[] }> };
        const ambiguities = detail.ambiguities || [{ handoff_id: detail.handoff_id || handoffs[0]?.handoff_id || "", keyword: detail.keyword || handoffs[0]?.keyword || "", candidates: detail.candidates || [] }];
        setLocationAmbiguities(ambiguities); setError(""); setErrorKind("LOCATION CONFIRMATION REQUIRED"); setInitState("location_confirmation_required");
      } else { setInitState("initialization_error"); showError(cause instanceof Error ? cause.message : "Candidate initialization failed", "INITIALIZATION ERROR"); }
    }
    finally { setBusy(false); }
  }

  async function attachHandoffs(targetProjectId = projectId) {
    if (!targetProjectId || !handoffs.length || attached) return;
    setBusy(true); setError("");
    try {
      const data = await request(`/projects/${targetProjectId}/handoffs/attach`, { method: "POST", body: JSON.stringify({ handoff_ids: handoffs.map(item => item.handoff_id) }) });
      setCandidateCount(Number(data.created_count || 0) + Number(data.existing_count || 0)); setAttached(true); await previewRun(targetProjectId);
    } catch (cause) { setInitializationFailed(true); showError(cause instanceof Error ? cause.message : "Handoff attachment failed", "INITIALIZATION ERROR"); }
    finally { setBusy(false); }
  }

  async function previewRun(targetProjectId = projectId) {
    if (!targetProjectId || !attached && !handoffs.length) return;
    try { setPreview(await request(`/projects/${targetProjectId}/validation-preview`, { method: "POST", body: JSON.stringify({ profile }) })); }
    catch (cause) { showError(cause instanceof Error ? cause.message : "Preview failed", "API ERROR"); }
  }

  async function startRun() {
    if (!projectId || !attached || candidateCount < 1) { showError("Attach at least one Search Volume handoff before starting.", "VALIDATION REJECTED"); return; }
    setBusy(true); setError("");
    try {
      const candidateIds = attachOutcomes.map(item => item.project_candidate_id).filter((id): id is string => Boolean(id));
      const created = await request(`/projects/${projectId}/runs`, { method: "POST", body: JSON.stringify({ profile, candidate_ids: candidateIds }) }) as Run;
      sessionStorage.setItem(runStorageKey(handoffs.map(item => item.handoff_id)), JSON.stringify({
        run_id: created.id,
        handoff_ids: handoffs.map(item => item.handoff_id),
        evidence_ids: handoffs.map(item => item.evidence_id),
        keywords: handoffs.map(item => item.keyword ?? ""),
        project_id: projectId,
        project_candidate_ids: candidateIds,
      } satisfies ActiveRunContext));
      setRun(created);
      setErrorKind("VALIDATION RUNNING");
      try {
        const completed = await request(`/runs/${created.id}/execute`, { method: "POST", body: JSON.stringify({ profile, candidate_ids: candidateIds }) }, 0) as Run;
        if (!runMatchesHandoffs(completed, handoffs, projectId)) throw new Error("Validation returned a run for a different handoff.");
        setRun(completed);
      } catch (cause) {
        if (!(cause instanceof DOMException && cause.name === "AbortError") && !(cause instanceof TypeError)) throw cause;
        setErrorKind("VALIDATION RUNNING");
        setError("Connection interrupted while waiting. Checking the existing run...");
        await pollRun(created.id, value => {
          if (!runMatchesHandoffs(value, handoffs, projectId)) throw new Error("Validation returned a run for a different handoff.");
          setRun(value);
        });
      }
    } catch (cause) { showError(cause instanceof Error ? cause.message : "Validation request failed", "RUN FAILED"); }
    finally { setBusy(false); }
  }

  return <AppShell active="Niche Validator">
    {run && <ReferenceRunView run={run} progress={progress} />}
    <header className="page-head"><div><p className="eyebrow">Rank &amp; Rent</p><h1>Rank &amp; Rent Validation Run</h1><p className="muted">Validate promising local keywords through Population -&gt; Search Volume -&gt; SERP -&gt; DA -&gt; Deeper Analysis -&gt; KD -&gt; Result.</p></div></header>
    {selected && <section className="card handoff-arrival"><div><strong>Imported from Search Volume</strong><h2>{selected.keyword}</h2><div className="handoff-meta"><span>SV {selected.search_volume ?? "Unavailable"}</span><span>{selected.provider}</span><span>Evidence reused</span><span>Status {selected.status}</span></div></div><span className="badge success">HANDOFF READY</span></section>}
    {handoffs.length > 1 && <section className="card selector-card"><label htmlFor="handoff-select">Search Volume handoff</label><select id="handoff-select" value={selected?.handoff_id || ""} onChange={event => setSelected(handoffs.find(item => item.handoff_id === event.target.value) || null)}>{handoffs.map(item => <option value={item.handoff_id} key={item.handoff_id}>{item.keyword} - SV {item.search_volume ?? "-"}</option>)}</select></section>}
    <section className="card lifecycle"><div className="stage-strip">{stages.map((stage, index) => <div className={`stage ${run ? (index === 0 ? "complete" : index === 1 ? "active" : "conditional") : index === 0 ? "active" : ""}`} key={stage}><span className="stage-circle">{index + 1}</span><span className="stage-name">{stage}</span><span className="stage-state">{run ? (index === 0 ? "Complete" : index === 1 ? "Current" : "Conditional") : index === 0 ? "Ready" : "Waiting"}</span></div>)}</div></section>
    <section className="run-grid"><section className="card card-body"><h2>Imported Rank &amp; Rent Candidate</h2><p className="muted">The handed-off Search Volume evidence is reused for validation.</p>{selected && <div className="handoff-meta"><strong>{selected.keyword}</strong><span>SV {selected.search_volume ?? "Unavailable"}</span><span>Evidence reused</span></div>}<label htmlFor="project-name">Project name<input id="project-name" value={project} onChange={event => setProject(event.target.value)} placeholder="Rank & Rent Project" /></label><div className="form-actions"><button className="button secondary" type="button" onClick={createProject} disabled={busy || !!projectId}>{projectId ? "Project ready" : "Create project"}</button><span className="muted">{projectId ? `Project ${projectId}` : initState === "initialization_error" ? "Project setup failed" : initState === "ready" ? "Project ready" : initState === "attaching_candidate" ? "Attaching candidate" : initState === "previewing" ? "Preparing preview" : "Setting up project"}</span></div><p className="muted">{initState === "ready" ? `${candidateCount} executable candidate(s) attached.` : initState === "initialization_error" ? "Candidate setup needs attention." : initState === "previewing" ? "Refreshing validation preview..." : "Setting up candidate..."}</p></section><section className="card card-body"><h2>Validation Profile</h2><div className="settings-grid"><Setting label="Population" value="20k - 120k" /><Setting label="Minimum SV" value="260" /><Setting label="DA gate" value="&lt; 10 / 4 required" /><Setting label="KD" value="Priority / 15" /></div></section></section>
    {attachOutcomes.length > 0 && <section className="card card-body mixed-summary"><h2>Mixed validation candidates</h2><div className="preview-grid"><Stat label="Candidates" value={attachOutcomes.length} /><Stat label="Ready" value={attachOutcomes.filter(item => item.status.endsWith("READY")).length} /><Stat label="Needs location" value={attachOutcomes.filter(item => item.status === "LOCAL_LOCATION_REQUIRED").length} /><Stat label="Local / General" value={`${attachOutcomes.filter(item => item.validation_scope === "LOCAL_RANK_RENT").length} / ${attachOutcomes.filter(item => item.validation_scope === "GENERAL_NICHE").length}`} /></div></section>}
    {attachOutcomes.length > 0 && <section className="mixed-candidate-grid">{attachOutcomes.map(item => { const handoff = handoffs.find(row => row.handoff_id === item.handoff_id); const general = item.validation_scope === "GENERAL_NICHE"; const pending = item.status === "LOCAL_LOCATION_REQUIRED"; return <article className="card card-body candidate-scope-card" key={item.handoff_id}><div className="progress-head"><h2>{item.keyword || handoff?.keyword || "Candidate"}</h2><span className="badge">{general ? "GENERAL NICHE" : "LOCAL RANK & RENT"}</span></div><p><strong>Status:</strong> {pending ? "LOCATION CONFIRMATION REQUIRED" : item.status === "GENERAL_READY" ? "READY" : item.status}</p>{general ? <><p><strong>Target:</strong> {handoff?.country_code || "US"}</p><p><strong>Location:</strong> Not required</p><p><strong>Population:</strong> NOT APPLICABLE</p><p><strong>SERP Mode:</strong> NATIONAL</p>{item.authority_opportunity && <div className="evidence-detail"><strong>Authority Opportunity: {item.authority_opportunity}</strong><span>Weak sites: {item.weak_site_count ?? "Unavailable"} / analyzed</span><span>Threshold: DA &lt; {item.authority_threshold ?? 20}</span>{item.authority_opportunity_reason && <small>{item.authority_opportunity_reason}</small>}</div>}<p className="muted">Pipeline: SV → National SERP → Authority Opportunity → Deep Analysis → KD → Result</p></> : <><p><strong>Population:</strong> {pending ? "Pending location" : "Applicable"}</p><p><strong>SERP Mode:</strong> Localized</p><p className="muted">Pipeline: Population → SV → Local SERP → Authority → Deep Analysis → KD → Result</p></>}</article>; })}</section>}
    {error && <div className="error-banner"><strong>{errorKind}</strong><span>{error}</span></div>}
    {locationAmbiguities.length > 0 && <section className="card card-body"><h2>Location confirmation required</h2><p className="muted">Choose a city for each keyword before validation continues.</p>{locationAmbiguities.map(item => <div className="location-choice" key={item.handoff_id}><strong>{item.keyword}</strong><span className="muted">Needs confirmation</span><div className="form-actions">{item.candidates.map(candidate => <button className="button secondary" type="button" key={candidate.city_id} onClick={() => chooseLocation(item.handoff_id, candidate)} disabled={busy}>{candidate.city}, {candidate.state}</button>)}</div></div>)}</section>}
    {locationCandidates.length > 0 && !locationAmbiguities.length && <section className="card card-body"><h2>Location confirmation required</h2><p className="muted">Select the intended city before Rank &amp; Rent validation continues.</p><div className="form-actions">{locationCandidates.map(candidate => <button className="button secondary" type="button" key={candidate.city_id} onClick={() => chooseLocation(handoffs[0]?.handoff_id || "", candidate)} disabled={busy}>{candidate.city}, {candidate.state}</button>)}</div></section>}
    <section className="card card-body preview-card"><div className="section-heading"><h2>Validation Preview</h2><p className="muted">Preview is zero-network. Downstream SERP, DA, Deep Analysis, and KD work is conditional on earlier gates.</p></div><div className="preview-footer"><span className="badge success">NO PROVIDER CALLS</span><button className="button secondary" type="button" onClick={() => previewRun()} disabled={!projectId || busy}>{busy ? "Preparing preview..." : "Refresh Preview"}</button></div>{preview && <div className="preview-grid"><Stat label="Candidates" value={preview.candidate_count} /><Stat label="Reusable SV" value={preview.reusable_search_volume ? `${preview.reusable_search_volume} · Reused` : "-"} /><Stat label="Estimated work" value={preview.estimated_provider_calls} /><Stat label="DA / KD" value="Conditional" /></div>}</section>
    {run && <section className="card card-body run-workspace"><div className="progress-head"><strong>Validation Run {run.id}</strong><span>{run.status}</span></div><div className="progress"><div className="progress-bar" style={{ width: `${progress}%` }} /></div><div className="run-meta"><span>Run progress {progress}%</span><span>Provider work is controlled by the backend</span><span>Evidence is persisted per stage</span></div>{run.candidate_results?.map((result, index) => { const general = result.validation_scope === "GENERAL_NICHE"; return <details className="run-result" key={index} open={run.candidate_results?.length === 1}><summary><strong>{result.keyword || "Candidate"}</strong> · {result.status === "ERROR_RETRYABLE" ? "RETRYABLE" : result.final_result}</summary><div className="stage-table">{[["Candidate Summary", result.status, general ? "General Niche candidate." : "Local Rank & Rent candidate."], ["Population", general ? "NOT APPLICABLE" : result.population, general ? "Not applicable — national/general candidates do not use city population filtering." : "City population filter applied."], ["Search Volume", result.search_volume_value != null ? `${result.search_volume_value} · Reused` : result.search_volume, "Search Volume evidence captured for this run."], ["SERP", result.serp, result.serp_reason === "SERP_PROVIDER_REQUEST_ERROR" ? "The SERP provider rejected the request; this is not a niche rejection." : result.serp === "RETRYABLE" ? `${result.serp_count || 0} usable organic results found; ${result.serp_required || 0} required.` : general ? "National US organic results collected." : "Localized organic results were collected."], ["Deep Analysis", result.deep_analysis, result.deep_analysis === "NOT RUN" ? "Not run; earlier gates did not qualify." : `${result.da_evidence?.length || 0} authority records captured.`], ["KD", result.kd, result.kd === "NOT RUN" ? "Not run; earlier gates did not qualify." : "Keyword difficulty evidence captured."], ["Final Assessment", result.final_result, result.final_result === "NOT PRODUCED" ? "No final decision was made." : "Final validation assessment."]].map(([stage, status, note]) => <div className="stage-row" key={stage}><strong>{stage}</strong><span>{status}</span><small>{note}</small></div>)}</div>{result.serp_evidence?.length ? <details className="evidence-section" open><summary><strong>SERP Evidence — {result.serp_evidence.length} captured</strong></summary><div className="evidence-detail">{result.serp_evidence.map(item => <span key={item.position}>#{item.position} {item.domain} · {item.url}</span>)}</div></details> : null}{result.da_evidence?.length ? <AuthorityEvidence records={result.da_evidence} general={general} /> : null}{result.reason_codes.length > 0 && <small>Technical details: {result.reason_codes.join(", ")}</small>}</details>; })}</section>}
    <section className="card card-body start-panel"><div><h2>{run ? "Validation Run" : "Start Validation"}</h2><p className="muted">The backend-confirmed candidate is ready. Starting validation may invoke configured downstream providers.</p><p className="muted">{candidateCount} executable candidate{candidateCount === 1 ? "" : "s"} ready.</p></div><button className="button primary" type="button" onClick={startRun} disabled={!!run || initState !== "ready" || !projectId || !attached || candidateCount < 1 || !preview || busy}>{busy ? "Validation running..." : run ? "Run already created" : "Start Validation"}</button></section>
  </AppShell>;
}

function ReferenceRunView({ run, progress }: { run: Run; progress: number }) {
  return <section className="reference-run-view">
    <div className="reference-run-header"><strong>Validation Run {run.id}</strong><span className="status-pill status-complete">{run.status}</span></div>
    <div className="reference-run-progress"><div className="progress"><div className="progress-bar" style={{ width: `${progress}%` }} /></div><span>{progress}%</span></div>
    {run.candidate_results?.map((result, index) => <ReferenceCandidate key={`${result.keyword}-${index}`} result={result} />)}
  </section>;
}

function ReferenceCandidate({ result }: { result: NonNullable<Run["candidate_results"]>[number] }) {
  const general = result.validation_scope === "GENERAL_NICHE";
  const evidence = result.da_evidence || [];
  const daCoverage = evidence.filter(item => item.da != null).length;
  const drCoverage = evidence.filter(item => item.ahrefs_dr != null).length;
  const rdCoverage = evidence.filter(item => item.referring_domains != null).length;
  const backlinkCoverage = evidence.filter(item => item.backlinks != null).length;
  const daWeak = evidence.filter(item => typeof item.da === "number" && item.da < 20).length;
  const drWeak = evidence.filter(item => typeof item.ahrefs_dr === "number" && item.ahrefs_dr < 20).length;
  const uniqueWeak = new Set(evidence.filter(item => (typeof item.da === "number" && item.da < 20) || (typeof item.ahrefs_dr === "number" && item.ahrefs_dr < 20)).map(item => item.domain || item.position)).size;
  const status = result.status === "ERROR_RETRYABLE" ? "RETRYABLE" : result.final_result;
  const authorityProviders = new Set(evidence.map(item => (item.da_provider || item.provider || "").toLowerCase()).filter(Boolean));
  const hasMockAuthority = authorityProviders.has("mock");
  const authorityLabel = authorityProviders.size === 1 && authorityProviders.has("moz") ? "Moz Coverage" : authorityProviders.size === 1 && authorityProviders.has("mock") ? "Mock Coverage" : "Authority Coverage";
  const authoritySource = authorityProviders.size === 1 && authorityProviders.has("moz") ? "Source: Moz" : authorityProviders.size === 1 && authorityProviders.has("mock") ? "Development evidence" : "Provider attribution shown below";
  const serpState = result.serp_evidence_state || (result.serp === "RETRYABLE" ? "PROVIDER ERROR" : result.serp === "PASS" ? "VALID" : "NOT AVAILABLE");
  const requestedDepth = result.serp_requested_depth ?? result.serp_required;
  const observedDepth = result.serp_observed_depth ?? result.serp_count;
  const coverageRatio = result.serp_coverage_ratio;
  const coverageText = requestedDepth != null && observedDepth != null ? `${observedDepth} / ${requestedDepth} (${coverageRatio != null ? `${Math.round(coverageRatio * 100)}%` : "Not available"})` : "Not available";
  const isPartial = serpState === "PARTIAL_VALID";
  const isInsufficient = serpState === "INSUFFICIENT";
  const opportunity = result.authority_opportunity || (uniqueWeak >= 4 ? "STRONG POTENTIAL" : uniqueWeak === 3 ? "GOOD POTENTIAL" : uniqueWeak ? "POTENTIAL NICHE" : "LOW OPPORTUNITY");
  return <article className="reference-candidate">
    <div className="candidate-title-row"><div className="candidate-title"><span className="candidate-icon">★</span><div><h2>{result.keyword || "Candidate"}</h2><p>{general ? "General Niche Candidate" : "Local Rank & Rent Candidate"}</p></div></div><span className={`status-pill ${status === "PASS" ? "status-complete" : "status-neutral"}`}>{status}</span></div>
    <div className="metric-card-grid">
      <MetricCard label="SERP Coverage" value={coverageText} note={`${serpState.replaceAll("_", " ")} · ${result.serp_provider || "Not available"}`} tone="blue" />
      <MetricCard label="Search Volume" value={result.search_volume_value?.toLocaleString() || "Not available"} note={`Source: ${result.search_volume_provider || "Not available"}`} tone="blue" />
      <MetricCard label="SERP Coverage" value={`${result.serp_count || 0} / ${result.serp_required || 0}`} note={`${serpState} · ${result.serp_provider || "Provider unavailable"}`} tone="blue" />
      <MetricCard label={authorityLabel} value={`${daCoverage} / ${evidence.length}`} note={authoritySource} tone="blue" />
      <MetricCard label="Ahrefs DR Coverage" value={`${drCoverage} / ${evidence.length}`} note="Source: Ahrefs" tone="violet" />
      <MetricCard label="RD Coverage" value={`${rdCoverage} / ${evidence.length}`} note="Source: DataForSEO" tone="green" />
      <MetricCard label="Backlink Coverage" value={`${backlinkCoverage} / ${evidence.length}`} note="Source: DataForSEO" tone="orange" />
      <MetricCard label="Unique Weak" value={`${uniqueWeak} / ${evidence.length}`} note={`DA < 20: ${daWeak} · DR < 20: ${drWeak}`} tone="red" />
      <MetricCard label="Opportunity" value={opportunity.replaceAll("_", " ")} note={result.authority_opportunity_reason || "Evidence-based opportunity"} tone="success" />
    </div>
    <div className="reference-stage-summary"><StageSummary label="Population" value={general ? "NOT APPLICABLE" : result.population} note={general ? "General niches do not use city population filtering" : "City evidence"} /><StageSummary label="Target" value={general ? "United States" : "Local city"} note={general ? "National / General" : "Resolved location"} /><StageSummary label="SERP Mode" value={general ? "National" : "Localized"} note="Organic results" /><StageSummary label="Deep Analysis" value={result.deep_analysis} note={`${evidence.length} authority records`} /><StageSummary label="KD" value={result.kd} note={result.kd === "NOT RUN" ? "Earlier gates did not qualify" : "Keyword evidence"} /><StageSummary label="Final Assessment" value={result.final_result} note="Final validation assessment" /></div>
    {hasMockAuthority && <div className="provenance-warning"><strong>DEVELOPMENT AUTHORITY EVIDENCE</strong><span>This run contains mock DA/PA values. These are not real Moz measurements and should be treated as provisional.</span></div>}
    {isPartial && <div className="coverage-note partial"><strong>PARTIAL SERP COVERAGE</strong><span>{coverageText} requested organic results were available. Validation continued using the observed competitors.</span></div>}
    {isInsufficient && <div className="coverage-note insufficient"><strong>INSUFFICIENT SERP EVIDENCE</strong><span>SERP evidence did not meet the configured minimum coverage.</span></div>}
    {isPartial && hasMockAuthority && !general && <div className="provisional-result"><strong>LOCAL RESULT: PROVISIONAL</strong><span>Reasons: SERP coverage is partial-valid; authority DA/PA is mock development evidence.</span></div>}
    <div className="coverage-summary"><strong>Coverage Summary</strong><span>{authorityLabel.replace(" Coverage", " DA/PA Coverage")} <b>{daCoverage}/{evidence.length}</b></span><span>Ahrefs DR <b>{drCoverage}/{evidence.length}</b></span><span>Referring Domains <b>{rdCoverage}/{evidence.length}</b></span><span>Backlinks <b>{backlinkCoverage}/{evidence.length}</b></span><span>DA &lt; 20 <b>{daWeak}</b></span><span>DR &lt; 20 <b>{drWeak}</b></span><span>Unique Weak <b>{uniqueWeak}</b></span></div>
    <div className="reference-pipeline"><span>Population</span><b>→</b><span>Search Volume</span><b>→</b><span>SERP</span><b>→</b><span>Authority</span><b>→</b><span>Deep Analysis</span><b>→</b><span>KD</span><b>→</b><span>Final Assessment</span></div>
    <div className={`serp-provenance serp-state-${serpState.toLowerCase().replaceAll(" ", "-")}`}><strong>{serpState === "PROVIDER ERROR" ? "SERP PROVIDER ERROR" : `${serpState} SERP EVIDENCE`}</strong><span>Provider: {result.serp_provider || "Provider unavailable"}</span><span>Target: {result.serp_target || (general ? "United States" : "Local target unavailable")}</span>{result.serp_fetched_at && <span>Fetched: {new Date(result.serp_fetched_at).toLocaleString()}</span>}{result.serp_snapshot_id && <span>Snapshot: {result.serp_snapshot_id}</span>}{result.serp_provider_status_code && <span>Status: {result.serp_provider_status_code} · {result.serp_provider_status_message || "Provider response error"}</span>}</div>
    <SerpEvidenceTable records={evidence} required={result.serp_required || 0} />
    <AuthorityEvidence records={evidence} general={general} />
    {hasMockAuthority && <p className="provenance-note">Authority assessment is provisional because mock DA/PA evidence was used{general ? ". Local DA gate evaluated using mock development authority evidence." : "."}</p>}
    <div className="metric-legend"><strong>Metric Legend</strong><span>DA &lt;20 = weak DA</span><span>DR &lt;20 = weak DR</span><span>MOZ = real Moz authority evidence</span><span>MOCK = development/test authority evidence</span><span>AHREFS = Ahrefs DR evidence</span><span>DATAFORSEO = backlink evidence</span><span>Not available = no persisted evidence</span></div>
  </article>;
}

function SerpEvidenceTable({ records, required }: { records: AuthorityRecord[]; required: number }) { return <section className="serp-table-section"><div className="evidence-heading"><strong>SERP Evidence</strong><span>{records.length} / {required || records.length} captured</span></div><div className="evidence-table-wrap"><table className="evidence-table serp-table"><thead><tr><th>Position</th><th>Domain</th><th>Page / URL</th><th>Status</th></tr></thead><tbody>{records.map(record => <tr key={`serp-${record.position}-${record.domain}`}><td>#{record.position}</td><td><a href={record.url || "#"} target="_blank" rel="noreferrer">{record.domain || "Not available"} ↗</a></td><td><span className="url-preview">{record.url || "Not available"}</span></td><td>{record.domain ? "CAPTURED" : "NOT AVAILABLE"}</td></tr>)}</tbody></table></div></section>; }

function MetricCard({ label, value, note, tone }: { label: string; value: string; note: string; tone: string }) { return <div className={`reference-metric tone-${tone}`}><span>{label}</span><strong>{value}</strong><small>{note}</small></div>; }
function StageSummary({ label, value, note }: { label: string; value: string; note: string }) { return <div><span>{label}</span><strong>{value}</strong><small>{note}</small></div>; }
function Setting({ label, value }: { label: string; value: string }) { return <div className="setting"><span>{label}</span><strong dangerouslySetInnerHTML={{ __html: value }} /></div>; }
function Stat({ label, value }: { label: string; value: unknown }) { return <div className="metric"><span>{label}</span><strong>{String(value ?? "-")}</strong></div>; }

function AuthorityEvidence({ records, general }: { records: AuthorityRecord[]; general: boolean }) {
  const daWeak = records.filter(record => typeof record.da === "number" && record.da < 20).length;
  const drWeak = records.filter(record => typeof record.ahrefs_dr === "number" && record.ahrefs_dr < 20).length;
  const uniqueWeak = new Set(records.filter(record => (typeof record.da === "number" && record.da < 20) || (typeof record.ahrefs_dr === "number" && record.ahrefs_dr < 20)).map(record => record.domain || record.position)).size;
  const providerFor = (record: AuthorityRecord) => (record.da_provider || record.provider || "").toLowerCase();
  const authorityProviders = new Set(records.map(providerFor).filter(Boolean));
  const heading = authorityProviders.size === 1 && authorityProviders.has("moz") ? "Moz DA/PA" : authorityProviders.size === 1 && authorityProviders.has("mock") ? "Mock DA/PA · Development Evidence" : "Authority DA/PA";
  const providerBadge = (record: AuthorityRecord) => { const provider = providerFor(record); return provider === "moz" ? "MOZ" : provider === "mock" ? "MOCK" : "NOT AVAILABLE"; };
  const providerText = (record: AuthorityRecord) => { const provider = providerFor(record); return provider === "moz" ? "Moz" : provider === "mock" ? "Mock development provider" : "Provider unavailable"; };
  return <details className="evidence-section" open><summary><strong>Domain Evidence — SERP, {heading}, Ahrefs & verified backlinks</strong></summary><div className="authority-summary"><span>{heading} coverage: {records.filter(record => record.da != null || record.pa != null).length}/{records.length}</span><span>Ahrefs DR coverage: {records.filter(record => record.ahrefs_dr != null).length}/{records.length}</span><span>RD coverage: {records.filter(record => record.referring_domains != null).length}/{records.length}</span><span>Backlink coverage: {records.filter(record => record.backlinks != null).length}/{records.length}</span>{general && <><span>DA &lt; 20: {daWeak}</span><span>DR &lt; 20: {drWeak}</span><span>Unique weak domains: {uniqueWeak}</span></>}</div><div className="evidence-table-wrap"><table className="evidence-table"><thead><tr><th>Pos.</th><th>Domain</th><th>DA</th><th>PA</th><th>Provider</th><th>DR</th><th>RDs</th><th>Backlinks</th><th>Signal</th><th>Actions</th></tr></thead><tbody>{records.map(record => { const daIsWeak = typeof record.da === "number" && record.da < 20; const drIsWeak = typeof record.ahrefs_dr === "number" && record.ahrefs_dr < 20; const signal = daIsWeak && drIsWeak ? "Weak DA + DR" : daIsWeak ? "Weak DA" : drIsWeak ? "Weak DR" : record.da == null && record.ahrefs_dr == null ? "Insufficient evidence" : "Strong competitor"; return <tr key={`${record.position}-${record.domain}`}><td>#{record.position}</td><td><details><summary>{record.domain || "Not available"}</summary><div className="domain-drawer"><strong>SERP</strong><span>Position #{record.position}</span><span>{record.url || "Not available"}</span><strong>Authority</strong><span>DA {record.da ?? "Not available"} · PA {record.pa ?? "Not available"} · {providerText(record)}</span><strong>Ahrefs</strong><span>DR {record.ahrefs_dr ?? "Not available"} · {record.dr_provider || "Provider unavailable"}</span><strong>DataForSEO Backlinks</strong><span>RDs {record.referring_domains ?? "Not available"} · Main domains {record.referring_main_domains ?? "Not available"} · IPs {record.referring_ips ?? "Not available"} · Subnets {record.referring_subnets ?? "Not available"} · Backlinks {record.backlinks ?? "Not available"}</span></div></details></td><td className={daIsWeak ? "metric metric-weak" : "metric"}>{record.da ?? "Not available"}</td><td className="metric metric-pa">{record.pa ?? "Not available"}</td><td><span className={`provider-badge provider-${providerBadge(record).toLowerCase().replace(" ", "-")}`} title={providerBadge(record) === "MOCK" ? "Development authority evidence — not real Moz data." : undefined}>{providerBadge(record)}</span></td><td className={drIsWeak ? "metric metric-weak" : "metric metric-dr"}>{record.ahrefs_dr ?? "Not available"}</td><td className="metric metric-rd">{record.referring_domains ?? "Not available"}</td><td className="metric metric-links">{record.backlinks ?? "Not available"}</td><td>{signal}</td><td><details><summary>Details</summary><small>{record.url || "Not available"}</small></details></td></tr>; })}</tbody></table></div></details>;
}
