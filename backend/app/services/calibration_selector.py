"""Select a conservative, information-rich manual Moz calibration queue."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.models.entities import ProxyAuthorityEvidence, ProxyBacklinkFeatureEvidence, SerpResultRow
from app.services.normalization import root_domain


@dataclass(frozen=True)
class CalibrationCandidate:
    domain: str
    ahrefs_dr: float
    dataforseo_rank: float | None
    referring_domains: int | None
    segment: str
    disagreement: bool
    selection_reason: str


def select_calibration_sample(db: Session, rows: Iterable[SerpResultRow], limit: int = 25) -> list[CalibrationCandidate]:
    """Return cached-Ahrefs domains weighted toward the DA<10 boundary.

    This is a queue selector only. It does not infer Moz DA, reject candidates,
    call a provider, or create a calibration observation.
    """
    if limit <= 0:
        return []
    domains = sorted({root_domain(row.url) or row.root_domain for row in rows})
    selected: list[CalibrationCandidate] = []
    backlink_features_available = "mapping_status" in {column["name"] for column in inspect(db.bind).get_columns("proxy_backlink_feature_evidence")}
    for domain in domains:
        ahrefs = db.scalar(select(ProxyAuthorityEvidence).where(ProxyAuthorityEvidence.root_domain == domain).order_by(ProxyAuthorityEvidence.fetched_at.desc()))
        if not ahrefs or ahrefs.domain_rating is None:
            continue
        backlink = None
        if backlink_features_available:
            backlink = db.scalar(select(ProxyBacklinkFeatureEvidence).where(ProxyBacklinkFeatureEvidence.target_domain == domain, ProxyBacklinkFeatureEvidence.mapping_status == "mapped").order_by(ProxyBacklinkFeatureEvidence.fetched_at.desc()))
        rank = backlink.rank if backlink else None
        disagreement = rank is not None and ((ahrefs.domain_rating <= 14 and rank > 100) or (ahrefs.domain_rating > 14 and rank < 100))
        if ahrefs.domain_rating <= 14:
            segment = "weak"
        elif ahrefs.domain_rating <= 30:
            segment = "borderline"
        elif ahrefs.domain_rating <= 60:
            segment = "medium"
        else:
            segment = "strong_control"
        selected.append(CalibrationCandidate(domain, ahrefs.domain_rating, rank, backlink.referring_domains if backlink else None, segment, disagreement, "signal_disagreement" if disagreement else f"{segment}_coverage"))

    # Disagreements teach the most. Reserve every requested segment before
    # filling remaining capacity so strong controls cannot be crowded out by
    # a large weak-domain pool.
    segment_order = {"weak": 0, "borderline": 1, "medium": 2, "strong_control": 3}
    selected.sort(key=lambda item: (0 if item.disagreement else 1, item.domain))
    buckets = {segment: [item for item in selected if item.segment == segment] for segment in segment_order}
    boundary = buckets["weak"] + buckets["borderline"]
    boundary.sort(key=lambda item: (0 if item.disagreement else 1, item.segment, item.domain))
    medium = buckets["medium"]
    controls = buckets["strong_control"]
    boundary_quota = min(len(boundary), max(1, round(limit * 0.60)))
    control_quota = min(len(controls), max(1, round(limit * 0.12)))
    medium_quota = min(len(medium), max(0, round(limit * 0.20)))
    chosen = boundary[:boundary_quota] + medium[:medium_quota] + controls[:control_quota]
    remaining = [item for item in selected if item not in chosen]
    remaining.sort(key=lambda item: (0 if item.disagreement else 1, segment_order[item.segment], item.domain))
    output = (chosen + remaining)[:limit]
    # Explicitly identify the next false-negative hunting queue without
    # changing production thresholds or making a rejection decision.
    return [CalibrationCandidate(x.domain, x.ahrefs_dr, x.dataforseo_rank, x.referring_domains, x.segment, x.disagreement, "POSITIVE-HUNT" if 8 <= x.ahrefs_dr <= 30 else x.selection_reason) for x in output]
