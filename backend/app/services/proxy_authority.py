from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    ManualMozObservation, ProxyAuthorityEvidence, ProxyCalibrationObservation,
    ProxyBacklinkFeatureEvidence, ProviderCache, ProviderCall, Run, RunCandidate, RunCandidateProxyAuthorityEvidence, RunCandidateBacklinkEvidence, SerpResultRow,
)
from app.providers.contracts import AuthorityTarget, ProxyAuthorityResult
from app.providers.factory import ahrefs_proxy_provider, dataforseo_backlink_proxy_provider
from app.services.cache_keys import evidence_is_fresh, provider_cache_key
from app.services.normalization import root_domain


PROXY_UNCALIBRATED = "UNCALIBRATED_HIGH_RECALL"


def select_interesting_backlink_rows(rows: Iterable[SerpResultRow], da_by_domain: dict[str, float | None], dr_by_domain: dict[str, float | None], threshold: float = 20.0) -> list[SerpResultRow]:
    """Conservative Option-C queue: enrich only domains with a weak DA/DR signal."""
    selected = []
    seen = set()
    for row in rows:
        domain = root_domain(row.url) or row.root_domain
        if domain in seen:
            continue
        seen.add(domain)
        if ((da_by_domain.get(domain) is not None and da_by_domain[domain] < threshold) or
                (dr_by_domain.get(domain) is not None and dr_by_domain[domain] < threshold)):
            selected.append(row)
    return selected


@dataclass(frozen=True)
class ProxyDecision:
    classification: str
    reason: str
    evidence: dict
    uncertainty: str
    recommended_action: str
    why_not_rejected: str | None = None


def evaluate_proxy(domain_ratings: list[float | None], threshold: float = 14.0,
                   minimum_weak: int = 4, ideal_weak: int = 5,
                   uncertainty_band: float = 5.0) -> ProxyDecision:
    """High-recall DR screening; never emits Moz PASS/IDEAL semantics."""
    observed = [value for value in domain_ratings if value is not None]
    weak = sum(value <= threshold for value in observed)
    borderline = sum(threshold < value <= threshold + uncertainty_band for value in observed)
    missing = len(domain_ratings) - len(observed)
    plausible = weak + borderline + missing
    evidence = {"metric": "ahrefs_domain_rating", "threshold": threshold, "weak_count": weak,
                "borderline_count": borderline, "missing_count": missing, "observed_count": len(observed),
                "minimum_weak": minimum_weak, "ideal_weak": ideal_weak, "calibration_state": PROXY_UNCALIBRATED}
    if weak >= ideal_weak:
        return ProxyDecision("PROXY_STRONG_CANDIDATE", f"{weak} domains are in the configured high-recall weak DR range.", evidence, "MODERATE_FALSE_POSITIVE_RISK", "MANUAL_MOZ_VALIDATION")
    if weak >= minimum_weak or plausible >= minimum_weak:
        return ProxyDecision("PROXY_REVIEW", f"{weak} domains are weak and {borderline} are borderline; the result could still contain {minimum_weak}+ Moz DA<10 domains.", evidence, "ELEVATED_FALSE_NEGATIVE_RISK_IF_REJECTED", "MANUAL_MOZ_VALIDATION", "Rejecting would carry unacceptable false-negative risk while uncalibrated evidence remains incomplete or borderline.")
    if missing == 0 and weak + borderline < minimum_weak:
        return ProxyDecision("PROXY_REJECTED_HIGH_CONFIDENCE", f"Only {plausible} domains are within the conservative weak/uncertainty range; maximum plausible count is below {minimum_weak}.", evidence, "LOW_FALSE_NEGATIVE_RISK_UNCALIBRATED", "REMOVE_FROM_MANUAL_QUEUE")
    return ProxyDecision("PROXY_DATA_INCOMPLETE", "Not enough DR evidence exists for a responsible high-recall decision.", evidence, "UNKNOWN", "MANUAL_MOZ_VALIDATION")


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def evaluate_run_candidate_proxy(db: Session, run: Run, rc: RunCandidate,
                                       rows: Iterable[SerpResultRow],
                                       threshold: float = 14.0,
                                       minimum_weak: int = 4,
                                       ideal_weak: int = 5,
                                       force_refresh: bool = False) -> ProxyDecision:
    # Ahrefs is domain-level evidence. Deduplicate SERP rows before deciding
    # which domains need a lookup, while preserving the first SERP row for
    # run-specific lineage.
    rows = list(rows)
    unique_rows = []
    seen_domains = set()
    for row in rows:
        domain = root_domain(row.url) or row.root_domain
        if domain in seen_domains:
            continue
        seen_domains.add(domain)
        unique_rows.append(row)
    rows = unique_rows
    ratings: list[float | None] = []
    cached_count = 0
    fetched_count = 0
    for row in rows:
        domain = root_domain(row.url) or row.root_domain
        key = provider_cache_key("ahrefs", "domain_rating", root_domain=domain)
        cache = db.scalar(select(ProviderCache).where(ProviderCache.cache_key == key))
        evidence = db.get(ProxyAuthorityEvidence, cache.evidence_id) if cache and cache.evidence_type == "proxy_authority" else None
        if evidence and not force_refresh and evidence_is_fresh(cache.fresh_until):
            ratings.append(evidence.domain_rating); cached_count += 1; continue
        result: ProxyAuthorityResult = (await ahrefs_proxy_provider().fetch([AuthorityTarget(row.url, domain)]))[0]
        evidence = ProxyAuthorityEvidence(target_url=row.url, root_domain=domain, provider="ahrefs", metric="domain_rating", domain_rating=result.domain_rating, source_kind="ahrefs_api", raw_payload=result.raw or {}, request_metadata={"endpoint": "/v3/public/domain-rating-free"}, fetched_at=_now(), fresh_until=_now() + timedelta(days=30))
        db.add(evidence); db.flush()
        if cache:
            cache.evidence_id = evidence.id; cache.fetched_at = evidence.fetched_at; cache.fresh_until = evidence.fresh_until; cache.status = "usable"
        else:
            db.add(ProviderCache(cache_key=key, provider="ahrefs", operation="domain_rating_free", evidence_type="proxy_authority", evidence_id=evidence.id, fetched_at=evidence.fetched_at, fresh_until=evidence.fresh_until))
        db.add(ProviderCall(provider="ahrefs", stage="proxy_authority", operation="domain_rating_free", request_cache_key=key, outcome="success", cache_hit=False, source_kind="ahrefs_api", units=0, started_at=evidence.fetched_at, finished_at=_now(), estimated_cost=0.0, actual_cost=0.0, run_id=run.id, run_candidate_id=rc.id))
        ratings.append(result.domain_rating); fetched_count += 1
        db.add(RunCandidateProxyAuthorityEvidence(run_candidate_id=rc.id, serp_result_row_id=row.id, proxy_authority_evidence_id=evidence.id, ranking_position=row.position, dr_value_used=evidence.domain_rating))
    # Cached evidence follows the same immutable SERP-row lineage as freshly fetched evidence.
    for row in rows:
        domain = root_domain(row.url) or row.root_domain
        key = provider_cache_key("ahrefs", "domain_rating", root_domain=domain)
        cache = db.scalar(select(ProviderCache).where(ProviderCache.cache_key == key))
        evidence = db.get(ProxyAuthorityEvidence, cache.evidence_id) if cache and cache.evidence_type == "proxy_authority" else None
        if evidence and not db.scalar(select(RunCandidateProxyAuthorityEvidence).where(RunCandidateProxyAuthorityEvidence.run_candidate_id == rc.id, RunCandidateProxyAuthorityEvidence.serp_result_row_id == row.id)):
            db.add(RunCandidateProxyAuthorityEvidence(run_candidate_id=rc.id, serp_result_row_id=row.id, proxy_authority_evidence_id=evidence.id, ranking_position=row.position, dr_value_used=evidence.domain_rating))
    decision = evaluate_proxy(ratings, threshold, minimum_weak, ideal_weak)
    result = dict(decision.evidence, targets_available=len(rows), targets_evaluated=len(rows), cache_hits=cached_count, network_lookups=fetched_count, unchecked_targets=0, decision=decision.classification, reason=decision.reason, uncertainty=decision.uncertainty, recommended_action=decision.recommended_action, why_not_rejected=decision.why_not_rejected)
    rc.proxy_classification = decision.classification
    rc.proxy_result = result
    run.proxy_provider = "ahrefs"; run.proxy_metric = "domain_rating"; run.proxy_calibration_version = "uncalibrated"; run.proxy_configuration_snapshot = {"threshold": threshold, "minimum_weak": minimum_weak, "ideal_weak": ideal_weak, "calibration_state": PROXY_UNCALIBRATED}
    db.commit()
    return decision


def add_manual_moz_observation(db: Session, domain: str, moz_da: float | None,
                               moz_pa: float | None = None, spam_score: float | None = None,
                               raw_payload: dict | None = None) -> ManualMozObservation:
    normalized = root_domain(domain) or domain.strip().lower()
    observation = ManualMozObservation(normalized_domain=normalized, moz_da=moz_da, moz_pa=moz_pa, spam_score=spam_score, raw_payload=raw_payload or {})
    db.add(observation); db.flush()
    ahrefs = db.scalar(select(ProxyAuthorityEvidence).where(ProxyAuthorityEvidence.root_domain == normalized).order_by(ProxyAuthorityEvidence.fetched_at.desc()))
    if ahrefs:
        db.add(ProxyCalibrationObservation(normalized_domain=normalized, ahrefs_dr=ahrefs.domain_rating, moz_da=moz_da, moz_da_below_10=moz_da < 10 if moz_da is not None else None, provenance="manual_moz", calibration_version="uncalibrated", feature_set_version="ahrefs_dr_v1", source_metadata={"manual_observation_id": observation.id}))
    db.commit(); return observation


async def enrich_backlink_features(db: Session, run: Run, rc: RunCandidate,
                                   rows: Iterable[SerpResultRow], force_refresh: bool = False) -> list[ProxyBacklinkFeatureEvidence]:
    """Fetch/cache DataForSEO backlink features independently from Moz and Ahrefs DR."""
    unique: dict[str, SerpResultRow] = {}
    for row in rows:
        domain = root_domain(row.url) or row.root_domain
        unique.setdefault(domain, row)
    evidence_by_domain: dict[str, ProxyBacklinkFeatureEvidence] = {}
    missing: list[AuthorityTarget] = []
    cache_keys: dict[str, str] = {}
    cache_records: dict[str, ProviderCache | None] = {}
    for domain, row in unique.items():
        key = provider_cache_key("dataforseo", "proxy_backlink_features", root_domain=domain, operation="backlinks_bulk_pages_summary_live")
        cache_keys[domain] = key
        cache = db.scalar(select(ProviderCache).where(ProviderCache.cache_key == key))
        cache_records[domain] = cache
        evidence = db.get(ProxyBacklinkFeatureEvidence, cache.evidence_id) if cache and cache.evidence_type == "proxy_backlink_features" else None
        if evidence and evidence.mapping_status == "mapped" and not force_refresh and evidence_is_fresh(cache.fresh_until):
            evidence_by_domain[domain] = evidence
        else:
            missing.append(AuthorityTarget(row.url, domain))
    if missing:
        provider = dataforseo_backlink_proxy_provider()
        results = await provider.fetch(missing)
        batch_fetched = _now()
        for target, result in zip(missing, results):
            fetched = _now(); fresh_until = fetched + timedelta(days=30)
            evidence = ProxyBacklinkFeatureEvidence(target_domain=target.root_domain, provider="dataforseo", operation=provider.operation, rank=result.rank, backlinks=result.backlinks, referring_domains=result.referring_domains, referring_main_domains=result.referring_main_domains, referring_ips=result.referring_ips, referring_subnets=result.referring_subnets, referring_domains_nofollow=result.referring_domains_nofollow, referring_main_domains_nofollow=result.referring_main_domains_nofollow, backlinks_spam_score=result.backlinks_spam_score, raw_payload={"item": getattr(result, "raw", None) or {}, "response": getattr(result, "response_raw", None) or {}}, request_metadata={"endpoint": provider.endpoint, "feature_set_version": "dataforseo_backlink_v1"}, fetched_at=fetched, fresh_until=fresh_until, actual_cost=result.actual_cost, api_status_code=result.api_status_code, api_status_message=result.api_status_message, mapping_status=getattr(result, "mapping_status", "mapped"), mapping_error=getattr(result, "mapping_error", None))
            db.add(evidence); db.flush(); evidence_by_domain[target.root_domain] = evidence
            existing_cache = cache_records[target.root_domain]
            if existing_cache:
                existing_cache.evidence_id = evidence.id
                existing_cache.fetched_at = fetched
                existing_cache.fresh_until = fresh_until
                existing_cache.status = "usable" if evidence.mapping_status == "mapped" else "invalid"
            else:
                db.add(ProviderCache(cache_key=cache_keys[target.root_domain], provider="dataforseo", operation=provider.operation, evidence_type="proxy_backlink_features", evidence_id=evidence.id, fetched_at=fetched, fresh_until=fresh_until))
        actual_cost = next((item.actual_cost for item in results if item.actual_cost is not None), None)
        mapping_failed = any(getattr(result, "mapping_status", "mapped") != "mapped" for result in results)
        db.add(ProviderCall(provider="dataforseo", stage="proxy_authority_enrichment", operation=provider.operation, request_cache_key=provider_cache_key("dataforseo", "proxy_backlink_batch", targets=sorted(cache_keys)), outcome="mapping_failure" if mapping_failed else "success", cache_hit=False, source_kind="dataforseo_backlinks", units=None, started_at=batch_fetched, finished_at=_now(), estimated_cost=provider.estimated_cost, actual_cost=actual_cost, run_id=run.id, run_candidate_id=rc.id, error_category="mapping" if mapping_failed else None, error_message="One or more target results lacked documented core backlink fields" if mapping_failed else None))
    run.proxy_configuration_snapshot = {**(run.proxy_configuration_snapshot or {}), "feature_sources": ["ahrefs.domain_rating", "dataforseo.backlink_summary"], "feature_set_version": "ahrefs_dr_v1+dataforseo_backlink_v1", "reject_audit_percent": run.proxy_reject_audit_percent or 0.0}
    db.commit()
    for domain, evidence in evidence_by_domain.items():
        row = unique[domain]
        if not db.scalar(select(RunCandidateBacklinkEvidence).where(RunCandidateBacklinkEvidence.run_candidate_id == rc.id, RunCandidateBacklinkEvidence.serp_result_row_id == row.id)):
            db.add(RunCandidateBacklinkEvidence(run_candidate_id=rc.id, serp_result_row_id=row.id, proxy_backlink_evidence_id=evidence.id, ranking_position=row.position))
    db.commit()
    return [evidence_by_domain[domain] for domain in unique]
