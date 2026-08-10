from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    AuthorityEvidence, CandidateEntity, CandidateEvent, CandidateStatus, City, ProjectCandidate,
    ProviderCache, ProviderCall, Run, RunCandidate, RunCandidateAuthorityEvidence,
    SearchVolumeEvidence, KeywordDifficultyEvidence, SerpResultRow, SerpSnapshot, PopulationEvidence,
)
from app.providers.contracts import AuthorityResult, AuthorityTarget, KeywordMetricRequest, SerpRequest
from app.providers.factory import authority_provider, search_volume_provider, serp_provider
from app.services.cache_keys import evidence_is_fresh, provider_cache_key
from app.services.gates import population_gate, search_volume_gate
from app.services.normalization import root_domain
from app.domain.freshness import FreshnessPolicy, can_reuse
from app.services.authority_evaluation import AuthorityEvaluationMode, evaluate_authority


def utc_now() -> datetime:
    """Return naive UTC for compatibility with the existing SQLite DateTime columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _event(db, rc, event_type, previous=None, resulting=None, reason=None, refs=None, metadata=None):
    db.add(CandidateEvent(
        run_id=rc.run_id, run_candidate_id=rc.id, project_candidate_id=rc.project_candidate_id,
        event_type=event_type, previous_status=previous, resulting_status=resulting,
        reason_code=reason, evidence_references=refs or {}, metadata_json=metadata or {},
    ))


def _call(db, run, rc, provider, stage, operation, key, outcome, source_kind, cache_hit=False, cost=0.0):
    db.add(ProviderCall(
        run_id=run.id, run_candidate_id=rc.id, provider=provider, stage=stage,
        operation=operation, request_cache_key=key, outcome=outcome,
        source_kind=source_kind, cache_hit=cache_hit, actual_cost=cost,
        execution_mode=(run.configuration_snapshot or {}).get("dataforseo_mode") if provider.startswith("dataforseo") else None,
    ))


def _set_status(rc, status, reason=None):
    rc.status = status
    if reason:
        rc.reason_codes = list(dict.fromkeys((rc.reason_codes or []) + [reason]))


def _fresh_cached(db: Session, key: str, evidence_type: str, model):
    cache = db.scalar(select(ProviderCache).where(ProviderCache.cache_key == key))
    if not cache or cache.evidence_type != evidence_type or not evidence_is_fresh(cache.fresh_until):
        return None
    evidence = db.get(model, cache.evidence_id)
    return evidence if evidence else None


def _policy_cached(db: Session, key: str, evidence_type: str, model, policy: str):
    """Return compatible evidence plus a stale-warning flag under run policy."""
    cache = db.scalar(select(ProviderCache).where(ProviderCache.cache_key == key))
    if not cache or cache.evidence_type != evidence_type:
        return None, False
    fresh = evidence_is_fresh(cache.fresh_until)
    reuse, warning = can_reuse(policy, fresh)
    evidence = db.get(model, cache.evidence_id) if reuse else None
    return (evidence, warning) if evidence else (None, False)


async def execute_run(db: Session, run_id: str, project_candidate_ids: list[str] | None = None) -> Run:
    run = db.get(Run, run_id)
    if not run:
        raise ValueError("Run not found")
    if run.status == "COMPLETED":
        return run
    run.status = "RUNNING"
    run.started_at = run.started_at or utc_now()
    db.flush()
    stmt = select(ProjectCandidate).where(ProjectCandidate.project_id == run.project_id)
    if project_candidate_ids:
        stmt = stmt.where(ProjectCandidate.id.in_(project_candidate_ids))
    candidates = db.scalars(stmt).all()
    counters = {"total_selected": len(candidates), "population_passed": 0, "population_rejected": 0,
                "sv_passed": 0, "sv_rejected": 0, "serp_ready": 0, "serp_incomplete": 0,
                "authority_completed": 0, "authority_incomplete": 0, "primary_passed": 0,
                "primary_rejected": 0, "provider_errors": 0, "cache_hits": 0, "provider_calls": 0}
    for pc in candidates:
        rc = db.scalar(select(RunCandidate).where(RunCandidate.run_id == run.id, RunCandidate.project_candidate_id == pc.id))
        if not rc:
            rc = RunCandidate(run_id=run.id, project_candidate_id=pc.id)
            db.add(rc); db.flush(); _event(db, rc, "RUN_CANDIDATE_STARTED", resulting=rc.status)
        if rc.finished_at:
            continue
        try:
            result = None
            entity_city = db.scalar(select(City).join(CandidateEntity, City.id == CandidateEntity.city_id).where(CandidateEntity.id == pc.candidate_entity_id))
            if entity_city is None:
                _set_status(rc, "ERROR_TERMINAL", "PROVIDER_ERROR"); counters["provider_errors"] += 1; continue
            pop_key = provider_cache_key("local", "population", city_id=entity_city.id, vintage=entity_city.population_vintage)
            pop = _fresh_cached(db, pop_key, "population", PopulationEvidence)
            if not pop:
                pop = PopulationEvidence(candidate_entity_id=pc.candidate_entity_id, city_id=entity_city.id, provider="local", source_kind="census_csv", population=entity_city.population, population_vintage=entity_city.population_vintage, raw_payload={"city": entity_city.name}, source_metadata={"city_id": entity_city.id}, fetched_at=utc_now(), fresh_until=utc_now()+timedelta(days=365))
                db.add(pop); db.flush(); db.add(ProviderCache(cache_key=pop_key, provider="local", operation="population", evidence_type="population", evidence_id=pop.id, fetched_at=pop.fetched_at, fresh_until=pop.fresh_until))
            rc.population_evidence_id = pop.id; _event(db, rc, "POPULATION_SELECTED", refs={"population_evidence_id": pop.id})
            decision = population_gate(pop.population, type("Profile", (), {"min_population": run.min_population, "max_population": run.max_population})())
            if not decision.passed:
                _set_status(rc, "POPULATION_REJECTED", decision.reason_codes[0]); counters["population_rejected"] += 1; rc.finished_at = utc_now(); continue
            counters["population_passed"] += 1; _event(db, rc, "POPULATION_PASSED", resulting="SV_PENDING")
            keyword = pc.display_keyword
            sv_key = provider_cache_key("mock", "search_volume", keyword=keyword, location=entity_city.name + ", " + entity_city.state_code, language=run.language_code, country=run.country_code)
            sv, sv_stale_warning = _policy_cached(db, sv_key, "search_volume", SearchVolumeEvidence, run.freshness_policy)
            if sv:
                counters["cache_hits"] += 1; _call(db, run, rc, sv.provider, "sv", "reuse", sv_key, "cache_hit", sv.source_kind, True)
                if sv_stale_warning: _event(db, rc, "STALE_EVIDENCE_REUSED", refs={"search_volume_evidence_id": sv.id}, metadata={"freshness_policy": run.freshness_policy, "stage": "search_volume"})
            else:
                result = (await search_volume_provider().fetch([KeywordMetricRequest(keyword, f"{entity_city.name}, {entity_city.state_code}, United States", run.language_code)]))[0]
                sv = SearchVolumeEvidence(candidate_entity_id=pc.candidate_entity_id, keyword=keyword, location_name=entity_city.name + ", " + entity_city.state_code, language_code=run.language_code, country_code=run.country_code, provider=result.provider, source_kind=result.provider, avg_monthly_searches=result.avg_monthly_searches, cpc=result.cpc, competition=result.competition, monthly_history=result.monthly_history, raw_payload=result.raw or {}, request_metadata={"location": entity_city.name}, fetched_at=utc_now(), fresh_until=utc_now()+timedelta(days=30))
                db.add(sv); db.flush(); db.add(ProviderCache(cache_key=sv_key, provider=sv.provider, operation="search_volume", evidence_type="search_volume", evidence_id=sv.id, fetched_at=sv.fetched_at, fresh_until=sv.fresh_until)); _call(db, run, rc, sv.provider, "sv", "fetch", sv_key, "success", sv.source_kind); counters["provider_calls"] += 1
            rc.search_volume_evidence_id = sv.id; _event(db, rc, "SV_SELECTED", refs={"search_volume_evidence_id": sv.id})
            if sv.avg_monthly_searches is None:
                _set_status(rc, "SV_REJECTED", "SV_MISSING"); counters["sv_rejected"] += 1; rc.finished_at = utc_now(); continue
            if sv.avg_monthly_searches < run.min_search_volume:
                _set_status(rc, "SV_REJECTED", "SV_BELOW_THRESHOLD"); counters["sv_rejected"] += 1; rc.finished_at = utc_now(); continue
            counters["sv_passed"] += 1; _event(db, rc, "SV_PASSED", resulting="SERP_PENDING")
            serp_key = provider_cache_key("mock", "serp", keyword=keyword, location=entity_city.name + ", " + entity_city.state_code, language=run.language_code, country=run.country_code, device="desktop")
            snap, serp_stale_warning = _policy_cached(db, serp_key, "serp", SerpSnapshot, run.freshness_policy)
            if snap and snap.requested_depth >= run.organic_depth:
                rows = db.scalars(select(SerpResultRow).where(SerpResultRow.snapshot_id == snap.id).order_by(SerpResultRow.position)).all()
                counters["cache_hits"] += 1; _call(db, run, rc, snap.provider, "serp", "reuse", serp_key, "cache_hit", snap.source_kind, True)
                if serp_stale_warning: _event(db, rc, "STALE_EVIDENCE_REUSED", refs={"serp_snapshot_id": snap.id}, metadata={"freshness_policy": run.freshness_policy, "stage": "serp"})
            else:
                serp = (await serp_provider().fetch([SerpRequest(keyword, f"{entity_city.name}, {entity_city.state_code}, United States", run.language_code, run.organic_depth)]))[0]
                snap = SerpSnapshot(candidate_id="pipeline", candidate_entity_id=pc.candidate_entity_id, provider=serp.provider, source_kind=serp.provider, keyword=keyword, location_name=entity_city.name + ", " + entity_city.state_code, language_code=run.language_code, country_code=run.country_code, requested_depth=run.organic_depth, raw_payload=serp.raw or {}, fetched_at=utc_now(), fresh_until=utc_now()+timedelta(days=7))
                db.add(snap); db.flush(); db.add(ProviderCache(cache_key=serp_key, provider=snap.provider, operation="serp", evidence_type="serp", evidence_id=snap.id, fetched_at=snap.fetched_at, fresh_until=snap.fresh_until)); _call(db, run, rc, snap.provider, "serp", "fetch", serp_key, "success", snap.source_kind); counters["provider_calls"] += 1
                rows=[]
                for item in serp.organic[:run.organic_depth]:
                    row=SerpResultRow(snapshot_id=snap.id, position=item.position, title=item.title, url=item.url, root_domain=root_domain(item.url)); db.add(row); rows.append(row)
                db.flush()
            rc.serp_snapshot_id = snap.id; _event(db, rc, "SERP_SELECTED", refs={"serp_snapshot_id": snap.id})
            if len(rows) < run.organic_depth:
                _set_status(rc, "ERROR_RETRYABLE", "SERP_INSUFFICIENT_ORGANIC_RESULTS"); counters["serp_incomplete"] += 1; rc.finished_at = utc_now(); continue
            rows = rows[:run.organic_depth]; counters["serp_ready"] += 1; _event(db, rc, "SERP_READY", resulting="AUTHORITY_PENDING")
            metrics=[]; metric_sources=[]; missing=[]
            for row in rows:
                authority_key = provider_cache_key("mock", "authority", target_url=row.url, root_domain=row.root_domain, target_type="URL")
                cached, stale_warning = _policy_cached(db, authority_key, "authority", AuthorityEvidence, run.freshness_policy)
                if cached:
                    metrics.append(AuthorityResult(row.url, row.root_domain, cached.da, cached.pa, cached.spam_score, cached.linking_root_domains, cached.backlinks, cached.provider, cached.raw_payload)); metric_sources.append((cached, stale_warning, authority_key))
                else:
                    metrics.append(None); metric_sources.append((None, False, authority_key)); missing.append(AuthorityTarget(row.url, row.root_domain))
            # ADAPTIVE authority is deliberately acquired as ordered batches.  A
            # normal full run still requests the complete unresolved set in one
            # batch; recalculation therefore never falls through to eager depth.
            fetched_queue = []
            unresolved_index = 0
            adaptive_recalculation = run.run_type == "RECALCULATION" and run.authority_evaluation_mode == "ADAPTIVE"
            batch_size = max(1, run.authority_batch_size) if adaptive_recalculation else max(1, len(missing))
            available=0; low=0
            fetched_count = 0
            observed_metrics = list(metrics)
            for row_index, (row, metric, source) in enumerate(zip(rows, metrics, metric_sources)):
                cached, stale_warning, authority_key = source
                if metric is None:
                    if not fetched_queue:
                        batch = missing[unresolved_index:unresolved_index + batch_size]
                        unresolved_index += len(batch)
                        fetched_queue = list(await authority_provider().fetch(batch))
                        fetched_count += len(fetched_queue)
                        counters["provider_calls"] += 1
                        if fetched_queue:
                            _call(db, run, rc, fetched_queue[0].provider, "authority", "batch_fetch", f"batch:{unresolved_index // batch_size}", "success", fetched_queue[0].provider)
                    metric = fetched_queue.pop(0)
                    observed_metrics[row_index] = metric
                    ev=AuthorityEvidence(candidate_entity_id=pc.candidate_entity_id, target_url=row.url, root_domain=row.root_domain, target_type="URL", provider=metric.provider, source_kind=metric.provider, da=metric.da, pa=metric.pa, spam_score=metric.spam_score, linking_root_domains=metric.linking_root_domains, backlinks=metric.backlinks, raw_payload=metric.raw or {}, fetched_at=utc_now(), fresh_until=utc_now()+timedelta(days=30)); db.add(ev); db.flush(); db.add(ProviderCache(cache_key=authority_key, provider=ev.provider, operation="authority", evidence_type="authority", evidence_id=ev.id, fetched_at=ev.fetched_at, fresh_until=ev.fresh_until)); counters["provider_calls"] += 1
                else:
                    ev = cached; _call(db, run, rc, ev.provider, "authority", "reuse", authority_key, "cache_hit", ev.source_kind, True); counters["cache_hits"] += 1
                    if stale_warning: _event(db, rc, "STALE_EVIDENCE_REUSED", refs={"authority_evidence_id": ev.id}, metadata={"freshness_policy": run.freshness_policy, "stage": "authority"})
                usable=metric.da is not None; available += int(usable); counted=bool(usable and metric.da < run.da_threshold); low += int(counted); db.add(RunCandidateAuthorityEvidence(run_candidate_id=rc.id, serp_result_row_id=row.id, authority_evidence_id=ev.id, ranking_position=row.position, da_value_used=metric.da, counted_as_low_da=counted))
                if adaptive_recalculation:
                    probe = evaluate_authority([m.da if m else None for m in observed_metrics], run.organic_depth, run.required_low_da_count, run.ideal_weak_domains, run.da_threshold, AuthorityEvaluationMode.ADAPTIVE, run.adaptive_seek_ideal, row_index + 1, fetched_count)
                    if probe.primary_gate_result in ("PASS", "PRIMARY_REJECTED"):
                        break
            if adaptive_recalculation:
                # Positions after the stopping point are intentionally unchecked,
                # even when compatible cache rows existed for them.
                evaluated_positions = row_index + 1 if rows else 0
                metrics = observed_metrics[:evaluated_positions] + [None] * max(0, len(rows) - evaluated_positions)
            minimum_weak = run.required_low_da_count
            evaluation = evaluate_authority([metric.da if metric else None for metric in metrics], run.organic_depth, minimum_weak, run.ideal_weak_domains, run.da_threshold, AuthorityEvaluationMode(run.authority_evaluation_mode), run.adaptive_seek_ideal, sum(1 for source in metric_sources if source[0] is not None), len(missing))
            rc.organic_results_evaluated=len(rows); rc.authority_results_available=available; rc.low_da_count=evaluation.confirmed_weak_count; rc.da_threshold_used=run.da_threshold; rc.required_low_da_count_used=minimum_weak; rc.minimum_weak_domains_used=minimum_weak; rc.ideal_weak_domains_used=run.ideal_weak_domains; rc.authority_evaluation_mode_used=run.authority_evaluation_mode; rc.adaptive_seek_ideal_used=run.adaptive_seek_ideal; rc.authority_targets_evaluated=evaluation.authority_targets_evaluated; rc.authority_targets_cached=evaluation.authority_targets_cached; rc.authority_targets_fetched=evaluation.authority_targets_fetched; rc.authority_targets_unchecked=evaluation.unchecked_remaining; rc.confirmed_weak_count=evaluation.confirmed_weak_count; rc.opportunity_classification=evaluation.opportunity_classification
            authority_complete = available == len(rows) or (adaptive_recalculation and evaluation.primary_gate_result != "ERROR_RETRYABLE")
            if not authority_complete:
                _set_status(rc, "ERROR_RETRYABLE", "DATA_INCOMPLETE"); counters["authority_incomplete"] += 1
            elif low < minimum_weak:
                _set_status(rc, "PRIMARY_REJECTED", "LOW_DA_COUNT_BELOW_REQUIRED"); rc.automatic_status="PRIMARY_REJECTED"; rc.primary_gate_passed=False; counters["primary_rejected"] += 1
            else:
                _set_status(rc, "PASS"); rc.automatic_status="PASS"; rc.primary_gate_passed=True; counters["primary_passed"] += 1
            # KD is evaluated only after the DA primary gate. It remains a
            # supporting signal and can never turn a DA failure into a pass.
            if run.kd_enabled:
                kd_key = provider_cache_key(sv.provider, "keyword_difficulty", keyword=keyword, location=entity_city.name + ", " + entity_city.state_code, language=run.language_code, country=run.country_code)
                kd, kd_stale_warning = _policy_cached(db, kd_key, "keyword_difficulty", KeywordDifficultyEvidence, run.freshness_policy)
                if kd and run.kd_provider == "moz" and kd.provider not in ("moz", "moz_csv", "mock"):
                    kd = None; kd_stale_warning = False
                if kd and run.kd_provider == "ahrefs" and kd.provider not in ("ahrefs", "ahrefs_csv"):
                    kd = None; kd_stale_warning = False
                if not kd and result is not None and result.keyword_difficulty is not None:
                    kd = KeywordDifficultyEvidence(candidate_entity_id=pc.candidate_entity_id, keyword=keyword, location_name=entity_city.name + ", " + entity_city.state_code, language_code=run.language_code, country_code=run.country_code, provider=sv.provider, metric_type="keyword_difficulty", difficulty=result.keyword_difficulty, source_kind=sv.source_kind, raw_payload=result.raw or {}, request_metadata={"shared_with_search_volume": True}, fetched_at=utc_now(), fresh_until=utc_now()+timedelta(days=30))
                    db.add(kd); db.flush(); db.add(ProviderCache(cache_key=kd_key, provider=kd.provider, operation="keyword_difficulty", evidence_type="keyword_difficulty", evidence_id=kd.id, fetched_at=kd.fetched_at, fresh_until=kd.fresh_until))
                if kd:
                    rc.keyword_difficulty_evidence_id = kd.id; rc.kd_value_used = kd.difficulty; rc.kd_status = "IDEAL" if kd.difficulty < run.kd_threshold else "ABOVE_PREFERRED"
                    if kd_stale_warning: _event(db, rc, "STALE_EVIDENCE_REUSED", refs={"keyword_difficulty_evidence_id": kd.id}, metadata={"freshness_policy": run.freshness_policy, "stage": "keyword_difficulty"})
                    if rc.primary_gate_passed and run.kd_mode == "HARD_GATE" and kd.difficulty >= run.kd_threshold:
                        _set_status(rc, "PRIMARY_REJECTED", "KD_ABOVE_THRESHOLD"); rc.automatic_status="PRIMARY_REJECTED"; rc.primary_gate_passed=False; counters["primary_rejected"] += 1
            counters["authority_completed"] += int(available == len(rows)); _event(db, rc, "PRIMARY_GATE_PASSED" if rc.primary_gate_passed else "PRIMARY_GATE_REJECTED", resulting=rc.status, metadata={"low_da_count": low, "available": available}); rc.finished_at=utc_now(); pc.current_status=rc.status; pc.automatic_status=rc.automatic_status; pc.current_reason_codes=rc.reason_codes; pc.latest_run_id=run.id
        except Exception as exc:
            _set_status(rc, "ERROR_RETRYABLE", "PROVIDER_ERROR"); counters["provider_errors"] += 1; rc.finished_at=utc_now(); db.add(CandidateEvent(run_id=run.id, run_candidate_id=rc.id, project_candidate_id=pc.id, event_type="EXECUTION_ERROR", resulting_status=rc.status, reason_code="PROVIDER_ERROR", metadata_json={"error": str(exc)}))
        db.flush()
    run.counters = counters; run.status="COMPLETED"; run.finished_at=utc_now(); db.commit(); db.refresh(run); return run
