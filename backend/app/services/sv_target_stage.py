"""Internal Search Volume evidence/target stage boundary."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import KeywordMetricEvidence, ProjectCandidate, Run, SearchVolumeEvidence, ProviderCache
from app.services.target_identity import targets_compatible


@dataclass(frozen=True)
class SvTargetStageResult:
    evidence: KeywordMetricEvidence | SearchVolumeEvidence | None
    stale_warning: bool
    target_mismatch: bool


def _policy_cached(db: Session, key: str, evidence_type: str, model, policy: str):
    # Kept local to this read/selection boundary; it performs no writes.
    from app.domain.freshness import can_reuse
    from app.services.cache_keys import evidence_is_fresh
    cache = db.scalar(select(ProviderCache).where(ProviderCache.cache_key == key))
    if not cache or cache.evidence_type != evidence_type:
        return None, False
    reuse, warning = can_reuse(policy, evidence_is_fresh(cache.fresh_until))
    evidence = db.get(model, cache.evidence_id) if reuse else None
    return (evidence, warning) if evidence else (None, False)


def select_sv_target_evidence(db: Session, candidate: ProjectCandidate, run: Run, keyword: str, cache_key: str) -> SvTargetStageResult:
    """Select canonical handoff evidence, then preserve legacy cache fallback."""
    evidence = db.get(KeywordMetricEvidence, candidate.search_volume_evidence_id) if candidate.search_volume_evidence_id else None
    target_mismatch = False
    if evidence and evidence.submitted_keyword.strip().casefold() != keyword.strip().casefold():
        evidence = None
    elif evidence and not targets_compatible(evidence.country_code, evidence.location_target, run.country_code):
        target_mismatch = True
        evidence = None
    elif evidence and evidence.language_code != run.language_code:
        evidence = None
    stale_warning = False
    if evidence is None and not target_mismatch:
        evidence, stale_warning = _policy_cached(db, cache_key, "search_volume", SearchVolumeEvidence, run.freshness_policy)
    return SvTargetStageResult(evidence=evidence, stale_warning=stale_warning, target_mismatch=target_mismatch)
