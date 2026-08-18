from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    AuthorityEvidence, CandidateEntity, CandidateEvent, CandidateStatus, City, ProjectCandidate,
    ProviderCache, ProviderCall, Run, RunCandidate, RunCandidateAuthorityEvidence,
    SearchVolumeEvidence, KeywordMetricEvidence, KeywordDifficultyEvidence, SerpResultRow, SerpSnapshot, PopulationEvidence, RunCandidateProxyAuthorityEvidence, ProxyAuthorityEvidence,
)
from app.providers.contracts import AuthorityResult, AuthorityTarget, KeywordMetricRequest, SerpRequest
from app.providers.factory import authority_provider, search_volume_provider, serp_provider
from app.services.cache_keys import evidence_is_fresh, provider_cache_key
from app.services.target_identity import targets_compatible
from app.services.sv_target_stage import select_sv_target_evidence
from app.services.serp_stage import build_serp_request, request_serp_and_classify
from app.services.serp_coverage import classify_serp_coverage, resolve_serp_policy
from app.services.evidence_compatibility import serp_snapshot_coverage
from app.services.authority_stage import evaluate_primary_authority
from app.services.ahrefs_stage import execute_ahrefs_stage, ahrefs_stage_not_executed
from app.services.gates import population_gate, search_volume_gate
from app.services.normalization import root_domain
from app.domain.freshness import FreshnessPolicy, can_reuse
from app.services.authority_evaluation import AuthorityEvaluationMode, evaluate_authority, evaluate_general_opportunity, evaluate_general_opportunity_metrics
from app.services.proxy_authority import evaluate_run_candidate_proxy, enrich_backlink_features, select_interesting_backlink_rows
from app.services.provider_location_registry import require_verified_mapping, ProviderLocationUnresolved
from app.services.provider_cache import upsert_provider_cache
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Return naive UTC for compatibility with the existing SQLite DateTime columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _event(db, rc, event_type, previous=None, resulting=None, reason=None, refs=None, metadata=None):
    db.add(CandidateEvent(
        run_id=rc.run_id, run_candidate_id=rc.id, project_candidate_id=rc.project_candidate_id,
        event_type=event_type, previous_status=previous, resulting_status=resulting,
        reason_code=reason, evidence_references=refs or {}, metadata_json=metadata or {},
    ))


def _call(db, run, rc, provider, stage, operation, key, outcome, source_kind,
          cache_hit=False, cost=0.0, telemetry=None):
    try:
        telemetry = telemetry or {}
        with db.begin_nested():
            db.add(ProviderCall(
                run_id=run.id, run_candidate_id=rc.id, provider=provider, stage=stage,
                operation=operation, request_cache_key=key, outcome=outcome,
                source_kind=source_kind, cache_hit=cache_hit, actual_cost=cost,
                execution_mode=(run.configuration_snapshot or {}).get("dataforseo_mode") if provider.startswith("dataforseo") else None,
                **telemetry,
            ))
            db.flush()
    except Exception as exc:
        logger.warning(
            "telemetry_write_failed provider=%s operation=%s run_id=%s run_candidate_id=%s exception=%s",
            provider, operation, run.id, rc.id, type(exc).__name__,
        )


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


def _policy_cached(db: Session, key: str, evidence_type: str, model, policy: str, *, requested_depth: int | None = None, minimum_organic_rows: int | None = None, minimum_organic_coverage: float | None = None):
    """Return compatible evidence plus a stale-warning flag under run policy."""
    cache = db.scalar(select(ProviderCache).where(ProviderCache.cache_key == key))
    if not cache or cache.evidence_type != evidence_type:
        return None, False
    fresh = evidence_is_fresh(cache.fresh_until)
    reuse, warning = can_reuse(policy, fresh)
    evidence = db.get(model, cache.evidence_id) if reuse else None
    if evidence_type == "serp" and evidence is not None and str(evidence.provider).startswith("dataforseo"):
        raw = evidence.raw_payload if isinstance(evidence.raw_payload, dict) else {}
        response = raw.get("response") if isinstance(raw.get("response"), dict) else {}
        status_code = response.get("status_code")
        row_count = db.query(SerpResultRow).filter(SerpResultRow.snapshot_id == evidence.id).count()
        coverage = serp_snapshot_coverage(evidence, observed_depth=row_count, requested_depth=requested_depth or evidence.requested_depth, minimum_organic_rows=minimum_organic_rows, minimum_organic_coverage=minimum_organic_coverage)
        if coverage.evidence_state.value in {"PROVIDER_ERROR", "INSUFFICIENT", "INVALID_TARGET"}:
            evidence = None
            warning = False
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
            rc = RunCandidate(run_id=run.id, project_candidate_id=pc.id, validation_scope=pc.validation_scope)
            db.add(rc); db.flush(); _event(db, rc, "RUN_CANDIDATE_STARTED", resulting=rc.status)
        if rc.finished_at:
            continue
        try:
            result = None
            entity_city = db.scalar(select(City).join(CandidateEntity, City.id == CandidateEntity.city_id).where(CandidateEntity.id == pc.candidate_entity_id))
            is_general = pc.validation_scope == "GENERAL_NICHE"
            if entity_city is None and not is_general:
                _set_status(rc, "ERROR_TERMINAL", "PROVIDER_ERROR"); counters["provider_errors"] += 1; continue
            location_name = f"{entity_city.name}, {entity_city.state_code}" if entity_city else run.country_code
            if not is_general:
                pop_key = provider_cache_key("local", "population", city_id=entity_city.id, vintage=entity_city.population_vintage)
                pop = _fresh_cached(db, pop_key, "population", PopulationEvidence)
                if not pop:
                    pop = PopulationEvidence(candidate_entity_id=pc.candidate_entity_id, city_id=entity_city.id, provider="local", source_kind="census_csv", population=entity_city.population, population_vintage=entity_city.population_vintage, raw_payload={"city": entity_city.name}, source_metadata={"city_id": entity_city.id}, fetched_at=utc_now(), fresh_until=utc_now()+timedelta(days=365))
                    db.add(pop); db.flush(); db.add(ProviderCache(cache_key=pop_key, provider="local", operation="population", evidence_type="population", evidence_id=pop.id, fetched_at=pop.fetched_at, fresh_until=pop.fresh_until))
                rc.population_evidence_id = pop.id; _event(db, rc, "POPULATION_SELECTED", refs={"population_evidence_id": pop.id})
                decision = population_gate(pop.population, type("Profile", (), {"population_enabled": True, "min_population": run.min_population, "max_population": run.max_population})())
                if not decision.passed:
                    _set_status(rc, "POPULATION_REJECTED", decision.reason_codes[0]); counters["population_rejected"] += 1; rc.finished_at = utc_now(); continue
                counters["population_passed"] += 1; _event(db, rc, "POPULATION_PASSED", resulting="SV_PENDING")
            else:
                _event(db, rc, "POPULATION_NOT_APPLICABLE", resulting="SV_PENDING", metadata={"reason": "General Niche candidates are not city-targeted."})
            keyword = pc.display_keyword
            sv_key = provider_cache_key("mock", "search_volume", keyword=keyword, location=location_name, language=run.language_code, country=run.country_code)
            # Search Volume handoffs point to the immutable keyword-metrics
            # evidence row. Keep the legacy SearchVolumeEvidence cache fallback
            # for older project candidates, but prefer the linked handoff row.
            sv_selection = select_sv_target_evidence(db, pc, run, keyword, sv_key)
            sv = sv_selection.evidence
            sv_target_mismatch = sv_selection.target_mismatch
            sv_stale_warning = sv_selection.stale_warning
            if sv:
                counters["cache_hits"] += 1; _call(db, run, rc, sv.provider, "sv", "reuse", sv_key, "cache_hit", sv.source_kind, True)
                if sv_stale_warning: _event(db, rc, "STALE_EVIDENCE_REUSED", refs={"search_volume_evidence_id": sv.id}, metadata={"freshness_policy": run.freshness_policy, "stage": "search_volume"})
            else:
                result = (await search_volume_provider().fetch([KeywordMetricRequest(keyword, location_name, run.language_code)]))[0]
                sv = SearchVolumeEvidence(candidate_entity_id=pc.candidate_entity_id, keyword=keyword, location_name=location_name, language_code=run.language_code, country_code=run.country_code, provider=result.provider, source_kind=result.provider, avg_monthly_searches=result.avg_monthly_searches, cpc=result.cpc, competition=result.competition, monthly_history=result.monthly_history, raw_payload=result.raw or {}, request_metadata={"location": location_name}, fetched_at=utc_now(), fresh_until=utc_now()+timedelta(days=30))
                db.add(sv); db.flush(); db.add(ProviderCache(cache_key=sv_key, provider=sv.provider, operation="search_volume", evidence_type="search_volume", evidence_id=sv.id, fetched_at=sv.fetched_at, fresh_until=sv.fresh_until)); _call(db, run, rc, sv.provider, "sv", "fetch", sv_key, "success", sv.source_kind); counters["provider_calls"] += 1
            if isinstance(sv, KeywordMetricEvidence):
                rc.keyword_metric_evidence_id = sv.id
                rc.search_volume_evidence_id = None
                _event(db, rc, "SV_SELECTED", refs={"keyword_metric_evidence_id": sv.id})
            else:
                rc.search_volume_evidence_id = sv.id
                _event(db, rc, "SV_SELECTED", refs={"search_volume_evidence_id": sv.id})
            if sv is None and sv_target_mismatch:
                _set_status(rc, "SV_REJECTED", "SV_TARGET_MISMATCH"); counters["sv_rejected"] += 1; rc.finished_at = utc_now(); continue
            if sv.avg_monthly_searches is None:
                _set_status(rc, "SV_REJECTED", "SV_MISSING"); counters["sv_rejected"] += 1; rc.finished_at = utc_now(); continue
            if sv.avg_monthly_searches < run.min_search_volume:
                _set_status(rc, "SV_REJECTED", "SV_BELOW_THRESHOLD"); counters["sv_rejected"] += 1; rc.finished_at = utc_now(); continue
            counters["sv_passed"] += 1; _event(db, rc, "SV_PASSED", resulting="SERP_PENDING")
            serp_key = provider_cache_key("mock", "serp", keyword=keyword, location=location_name, language=run.language_code, country=run.country_code, device="desktop")
            snap, serp_stale_warning = _policy_cached(db, serp_key, "serp", SerpSnapshot, run.freshness_policy, requested_depth=run.organic_depth, minimum_organic_rows=run.minimum_organic_rows, minimum_organic_coverage=run.minimum_organic_coverage)
            if snap:
                rows = db.scalars(select(SerpResultRow).where(SerpResultRow.snapshot_id == snap.id).order_by(SerpResultRow.position)).all()
                counters["cache_hits"] += 1; _call(db, run, rc, snap.provider, "serp", "reuse", serp_key, "cache_hit", snap.source_kind, True)
                if serp_stale_warning: _event(db, rc, "STALE_EVIDENCE_REUSED", refs={"serp_snapshot_id": snap.id}, metadata={"freshness_policy": run.freshness_policy, "stage": "serp"})
            else:
                provider_location_code = 2840 if is_general and run.country_code == "US" else None
                if not is_general and entity_city and get_settings().nicheforge_serp_provider == "dataforseo":
                    try:
                        provider_location_code = require_verified_mapping(db, entity_city, "dataforseo").location_code
                    except ProviderLocationUnresolved:
                        _set_status(rc, "ERROR_RETRYABLE", "PROVIDER_LOCATION_UNRESOLVED")
                        counters["provider_errors"] += 1
                        rc.finished_at = utc_now()
                        continue
                serp_request = build_serp_request(keyword, location_name, run.language_code, run.organic_depth, run.country_code, provider_location_code)
                minimum_organic_rows, minimum_organic_coverage = resolve_serp_policy(requested_depth=run.organic_depth, minimum_organic_rows=run.minimum_organic_rows, minimum_organic_coverage=run.minimum_organic_coverage)
                serp_stage = await request_serp_and_classify(serp_provider(), serp_request, minimum_organic_rows=minimum_organic_rows, minimum_organic_coverage=minimum_organic_coverage)
                serp = serp_stage.result
                if serp_stage.reason_code == "SERP_PROVIDER_REQUEST_ERROR":
                    _call(db, run, rc, serp.provider, "serp", "fetch", serp_key, "error", serp.provider, False)
                    _set_status(rc, serp_stage.status, serp_stage.reason_code)
                    counters["provider_errors"] += 1
                    rc.finished_at = utc_now()
                    db.add(CandidateEvent(run_id=run.id, run_candidate_id=rc.id, project_candidate_id=pc.id, event_type="SERP_PROVIDER_ERROR", resulting_status=rc.status, reason_code=serp_stage.reason_code, metadata_json={"provider_status_code": serp_stage.provider_status_code, "provider_status_message": serp_stage.provider_status_message}))
                    continue
                snap = SerpSnapshot(candidate_id="pipeline", candidate_entity_id=pc.candidate_entity_id, provider=serp.provider, source_kind=serp.provider, keyword=keyword, location_name=location_name, language_code=run.language_code, country_code=run.country_code, requested_depth=run.organic_depth, raw_payload=serp.raw or {}, fetched_at=utc_now(), fresh_until=utc_now()+timedelta(days=7))
                db.add(snap); db.flush()
                rows=[]
                for item in serp.organic[:run.organic_depth]:
                    row=SerpResultRow(snapshot_id=snap.id, position=item.position, title=item.title, url=item.url, root_domain=root_domain(item.url)); db.add(row); rows.append(row)
                db.flush()
                upsert_provider_cache(db, cache_key=serp_key, provider=snap.provider, operation="serp", evidence_type="serp", evidence_id=snap.id, fetched_at=snap.fetched_at, fresh_until=snap.fresh_until)
                _call(db, run, rc, snap.provider, "serp", "fetch", serp_key, "success", snap.source_kind); counters["provider_calls"] += 1
            rc.serp_snapshot_id = snap.id; _event(db, rc, "SERP_SELECTED", refs={"serp_snapshot_id": snap.id})
            minimum_organic_rows, minimum_organic_coverage = resolve_serp_policy(requested_depth=run.organic_depth, minimum_organic_rows=run.minimum_organic_rows, minimum_organic_coverage=run.minimum_organic_coverage)
            coverage = classify_serp_coverage(requested_depth=run.organic_depth, usable_organic_count=len(rows), minimum_organic_rows=minimum_organic_rows, minimum_organic_coverage=minimum_organic_coverage)
            if not coverage.sufficient_for_downstream:
                _set_status(rc, "ERROR_RETRYABLE", "SERP_INSUFFICIENT_ORGANIC_RESULTS"); counters["serp_incomplete"] += 1; rc.finished_at = utc_now(); continue
            rows = rows[:run.organic_depth]; counters["serp_ready"] += 1; _event(db, rc, "SERP_READY", resulting="AUTHORITY_PENDING", metadata={"evidence_state": coverage.evidence_state, "requested_depth": coverage.requested_depth, "observed_depth": coverage.usable_organic_count, "coverage_ratio": coverage.coverage_ratio})
            authority_occurrences = len(rows)
            authority_urls = {row.url for row in rows}
            authority_domains = {row.root_domain for row in rows}
            authority_metadata = {
                "authority_occurrence_count": authority_occurrences,
                "unique_url_count": len(authority_urls),
                "unique_domain_count": len(authority_domains),
                "same_url_duplicate_count": authority_occurrences - len(authority_urls),
                "same_domain_different_url_count": len(authority_urls) - len(authority_domains),
            }
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
            authority_batch_count = 0
            authority_items_failed = 0
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
                        authority_items_failed += max(0, len(batch) - len(fetched_queue))
                        authority_batch_count += 1
                        counters["provider_calls"] += 1
                        if fetched_queue:
                            _call(
                                db, run, rc, fetched_queue[0].provider, "authority", "batch_fetch",
                                f"batch:{unresolved_index // batch_size}", "success",
                                fetched_queue[0].provider,
                                telemetry={
                                    "logical_item_count": len(batch),
                                    "unique_target_count": len({target.url for target in batch}),
                                    "cache_miss_count": len(batch),
                                    "provider_item_count": len(fetched_queue),
                                    "items_returned_count": len(fetched_queue),
                                    "items_failed_count": max(0, len(batch) - len(fetched_queue)),
                                    "evidence_created_count": len(fetched_queue),
                                    "batch_id": f"{run.id}:{rc.id}:{unresolved_index // batch_size}",
                                    "batch_size": len(batch),
                                    "batch_count": 1,
                                    "http_request_count": 1,
                                    "retry_count": 0,
                                    "http_request_sent": True,
                                    "actual_evidence_provider": fetched_queue[0].provider,
                                    "cache_provider_dimension": "mock",
                                    "cost_confidence": "UNKNOWN",
                                },
                            )
                    metric = fetched_queue.pop(0)
                    observed_metrics[row_index] = metric
                    ev=AuthorityEvidence(candidate_entity_id=pc.candidate_entity_id, target_url=row.url, root_domain=row.root_domain, target_type="URL", provider=metric.provider, source_kind=metric.provider, da=metric.da, pa=metric.pa, spam_score=metric.spam_score, linking_root_domains=metric.linking_root_domains, backlinks=metric.backlinks, raw_payload=metric.raw or {}, fetched_at=utc_now(), fresh_until=utc_now()+timedelta(days=30)); db.add(ev); db.flush(); db.add(ProviderCache(cache_key=authority_key, provider=ev.provider, operation="authority", evidence_type="authority", evidence_id=ev.id, fetched_at=ev.fetched_at, fresh_until=ev.fresh_until)); counters["provider_calls"] += 1
                else:
                    ev = cached
                    _call(
                        db, run, rc, ev.provider, "authority", "reuse", authority_key,
                        "cache_hit", ev.source_kind, True,
                        telemetry={
                            "logical_item_count": 1,
                            "unique_target_count": 1,
                            "cache_hit_count": 1,
                            "stale_count": int(stale_warning),
                            "cache_outcome": "STALE_REUSED" if stale_warning else "HIT_FRESH",
                            "evidence_reused_count": 1,
                            "actual_evidence_provider": ev.provider,
                            "cache_provider_dimension": "mock",
                            "http_request_count": 0,
                            "retry_count": 0,
                            "http_request_sent": False,
                            "cost_confidence": "UNKNOWN",
                            "metadata_json": {
                                "authority_occurrence_count": 1,
                                "unique_url_count": 1,
                                "unique_domain_count": 1,
                                "same_url_duplicate_count": 0,
                                "same_domain_different_url_count": 0,
                            },
                        },
                    )
                    counters["cache_hits"] += 1
                    if stale_warning: _event(db, rc, "STALE_EVIDENCE_REUSED", refs={"authority_evidence_id": ev.id}, metadata={"freshness_policy": run.freshness_policy, "stage": "authority"})
                usable=metric.da is not None; available += int(usable); counted=bool(usable and metric.da < run.da_threshold); low += int(counted); db.add(RunCandidateAuthorityEvidence(run_candidate_id=rc.id, serp_result_row_id=row.id, authority_evidence_id=ev.id, ranking_position=row.position, da_value_used=metric.da, counted_as_low_da=counted))
                if adaptive_recalculation:
                    probe = evaluate_primary_authority(observed_metrics, observed_depth=len(observed_metrics), required_weak=run.required_low_da_count, ideal_weak=run.ideal_weak_domains, da_threshold=run.da_threshold, mode=AuthorityEvaluationMode.ADAPTIVE, adaptive_seek_ideal=run.adaptive_seek_ideal, cached_count=row_index + 1, missing_count=fetched_count).evaluation
                    if probe.primary_gate_result in ("PASS", "PRIMARY_REJECTED"):
                        break
            if adaptive_recalculation:
                # Positions after the stopping point are intentionally unchecked,
                # even when compatible cache rows existed for them.
                evaluated_positions = row_index + 1 if rows else 0
                metrics = observed_metrics[:evaluated_positions] + [None] * max(0, len(rows) - evaluated_positions)
            authority_cache_hits = sum(1 for cached, _, _ in metric_sources if cached is not None)
            authority_stale_count = sum(1 for _, stale, _ in metric_sources if stale)
            authority_cache_misses = len(missing)
            authority_cache_outcome = (
                "HIT_FRESH" if authority_cache_hits == authority_occurrences and authority_stale_count == 0
                else "MIXED" if authority_cache_hits and authority_cache_misses
                else "MISS_NOT_FOUND" if authority_cache_misses
                else "STALE_REUSED" if authority_stale_count
                else "NOT_CACHEABLE"
            )
            actual_authority_provider = next(
                (metric.provider for metric in metrics if metric is not None),
                "moz",
            )
            _call(
                db, run, rc, actual_authority_provider, "authority", "authority_summary",
                f"summary:{rc.id}",
                "success" if authority_batch_count else "cache_hit",
                actual_authority_provider,
                cache_hit=authority_batch_count == 0,
                telemetry={
                    "logical_item_count": authority_occurrences,
                    "unique_target_count": len(authority_urls),
                    "cache_hit_count": authority_cache_hits,
                    "cache_miss_count": authority_cache_misses,
                    "stale_count": authority_stale_count,
                    "cache_outcome": authority_cache_outcome,
                    "cache_provider_dimension": "mock",
                    "actual_evidence_provider": actual_authority_provider,
                    "evidence_reused_count": authority_cache_hits,
                    "evidence_created_count": fetched_count,
                    "evidence_partial_count": sum(1 for metric in metrics if metric and (metric.da is None or metric.pa is None)),
                    "evidence_missing_count": sum(1 for metric in metrics if metric is None),
                    "provider_item_count": fetched_count,
                    "items_returned_count": fetched_count,
                    "items_failed_count": authority_items_failed,
                    "batch_count": authority_batch_count,
                    "http_request_count": authority_batch_count,
                    "retry_count": 0,
                    "http_request_sent": authority_batch_count > 0,
                    "paid_attempt": None,
                    "cost_confidence": "UNKNOWN",
                    "metadata_json": authority_metadata,
                },
            )
            settings = get_settings()
            if settings.ahrefs_proxy_enabled and settings.ahrefs_live_approved:
                ahrefs_stage = await execute_ahrefs_stage(db, run, rc, rows, threshold=14.0, minimum_weak=4, ideal_weak=5)
            else:
                ahrefs_stage = ahrefs_stage_not_executed(rows)
            minimum_weak = run.required_low_da_count
            authority_stage = evaluate_primary_authority(metrics, observed_depth=len(rows), required_weak=minimum_weak, ideal_weak=run.ideal_weak_domains, da_threshold=run.da_threshold, mode=AuthorityEvaluationMode(run.authority_evaluation_mode), adaptive_seek_ideal=run.adaptive_seek_ideal, cached_count=sum(1 for source in metric_sources if source[0] is not None), missing_count=len(missing))
            evaluation = authority_stage.evaluation
            general_opportunity = evaluate_general_opportunity([metric.da if metric else None for metric in metrics], 20.0) if is_general else None
            if is_general and settings.ahrefs_proxy_enabled and settings.ahrefs_live_approved:
                dr_by_row = {row.id: ahrefs_stage.dr_by_domain.get(root_domain(row.url) or row.root_domain) for row in rows}
                general_opportunity = evaluate_general_opportunity_metrics([metric.da if metric else None for metric in metrics], [dr_by_row.get(row.id) for row in rows], 20.0)
            rc.organic_results_evaluated=len(rows); rc.authority_results_available=available; rc.low_da_count=evaluation.confirmed_weak_count; rc.da_threshold_used=run.da_threshold; rc.required_low_da_count_used=minimum_weak; rc.minimum_weak_domains_used=minimum_weak; rc.ideal_weak_domains_used=run.ideal_weak_domains; rc.authority_evaluation_mode_used=run.authority_evaluation_mode; rc.adaptive_seek_ideal_used=run.adaptive_seek_ideal; rc.authority_targets_evaluated=evaluation.authority_targets_evaluated; rc.authority_targets_cached=evaluation.authority_targets_cached; rc.authority_targets_fetched=evaluation.authority_targets_fetched; rc.authority_targets_unchecked=evaluation.unchecked_remaining; rc.confirmed_weak_count=evaluation.confirmed_weak_count; rc.opportunity_classification=evaluation.opportunity_classification
            if general_opportunity:
                rc.low_da_count = general_opportunity.weak_count; rc.da_threshold_used = general_opportunity.threshold; rc.opportunity_classification = general_opportunity.classification; rc.authority_opportunity_reason = general_opportunity.reason
            authority_complete = available == len(rows) or (adaptive_recalculation and evaluation.primary_gate_result != "ERROR_RETRYABLE")
            if not authority_complete:
                _set_status(rc, "ERROR_RETRYABLE", "DATA_INCOMPLETE"); counters["authority_incomplete"] += 1
            elif is_general:
                _set_status(rc, "PASS"); rc.automatic_status = general_opportunity.classification if general_opportunity else "POTENTIAL_NICHE"; rc.primary_gate_passed = True; counters["primary_passed"] += 1
            elif low < minimum_weak:
                _set_status(rc, "PRIMARY_REJECTED", "LOW_DA_COUNT_BELOW_REQUIRED"); rc.automatic_status="PRIMARY_REJECTED"; rc.primary_gate_passed=False; counters["primary_rejected"] += 1
            else:
                _set_status(rc, "PASS"); rc.automatic_status="PASS"; rc.primary_gate_passed=True; counters["primary_passed"] += 1
            if settings.dataforseo_backlink_proxy_enabled and settings.dataforseo_backlink_live_approved and rc.primary_gate_passed:
                da_by_domain = {row.root_domain: (metric.da if metric else None) for row, metric in zip(rows, metrics)}
                dr_links = db.scalars(select(RunCandidateProxyAuthorityEvidence).where(RunCandidateProxyAuthorityEvidence.run_candidate_id == rc.id)).all()
                dr_by_domain = {row.root_domain: link.dr_value_used for row, link in zip(rows, dr_links)}
                backlink_rows = select_interesting_backlink_rows(rows, da_by_domain, dr_by_domain, 20.0)
                if backlink_rows:
                    await enrich_backlink_features(db, run, rc, backlink_rows)
            # KD is evaluated only after the DA primary gate. It remains a
            # supporting signal and can never turn a DA failure into a pass.
            if run.kd_enabled:
                kd_key = provider_cache_key(sv.provider, "keyword_difficulty", keyword=keyword, location=location_name, language=run.language_code, country=run.country_code)
                kd, kd_stale_warning = _policy_cached(db, kd_key, "keyword_difficulty", KeywordDifficultyEvidence, run.freshness_policy)
                if kd and run.kd_provider == "moz" and kd.provider not in ("moz", "moz_csv", "mock"):
                    kd = None; kd_stale_warning = False
                if kd and run.kd_provider == "ahrefs" and kd.provider not in ("ahrefs", "ahrefs_csv"):
                    kd = None; kd_stale_warning = False
                if not kd and result is not None and result.keyword_difficulty is not None:
                    kd = KeywordDifficultyEvidence(candidate_entity_id=pc.candidate_entity_id, keyword=keyword, location_name=location_name, language_code=run.language_code, country_code=run.country_code, provider=sv.provider, metric_type="keyword_difficulty", difficulty=result.keyword_difficulty, source_kind=sv.source_kind, raw_payload=result.raw or {}, request_metadata={"shared_with_search_volume": True}, fetched_at=utc_now(), fresh_until=utc_now()+timedelta(days=30))
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
