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

    # Disagreements teach the most; preserve deterministic ordering within each
    # segment and then fill the requested queue without inventing metrics.
    segment_order = {"weak": 0, "borderline": 1, "medium": 2, "strong_control": 3}
    selected.sort(key=lambda item: (0 if item.disagreement else 1, segment_order[item.segment], item.domain))
    return selected[:limit]
