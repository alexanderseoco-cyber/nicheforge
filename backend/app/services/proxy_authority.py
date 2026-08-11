from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    ManualMozObservation, ProxyAuthorityEvidence, ProxyCalibrationObservation,
    ProviderCache, ProviderCall, Run, RunCandidate, SerpResultRow,
)
from app.providers.contracts import AuthorityTarget, ProxyAuthorityResult
from app.providers.factory import ahrefs_proxy_provider
from app.services.cache_keys import evidence_is_fresh, provider_cache_key
from app.services.normalization import root_domain


PROXY_UNCALIBRATED = "UNCALIBRATED_HIGH_RECALL"


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
    rows = list(rows)
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
        db.add(ProxyCalibrationObservation(normalized_domain=normalized, ahrefs_dr=ahrefs.domain_rating, moz_da=moz_da, provenance="manual_moz", calibration_version="uncalibrated", source_metadata={"manual_observation_id": observation.id}))
    db.commit(); return observation
