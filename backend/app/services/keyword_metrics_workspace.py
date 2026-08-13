from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.models.entities import KeywordMetricEvidence


@dataclass(frozen=True)
class KeywordMetricsFilter:
    min_search_volume: int | None = None
    max_search_volume: int | None = None
    provider: str | None = None
    mapping_status: str | None = None
    sort_by: str = "avg_monthly_searches"
    descending: bool = True


def filter_and_sort_evidence(evidence: list[KeywordMetricEvidence], criteria: KeywordMetricsFilter) -> list[KeywordMetricEvidence]:
    """Research-only filtering; never applies validation gates or mutates evidence."""
    items = [x for x in evidence if (criteria.provider is None or x.provider == criteria.provider)
        and (criteria.mapping_status is None or x.mapping_status == criteria.mapping_status)
        and (criteria.min_search_volume is None or (x.avg_monthly_searches is not None and x.avg_monthly_searches >= criteria.min_search_volume))
        and (criteria.max_search_volume is None or (x.avg_monthly_searches is not None and x.avg_monthly_searches <= criteria.max_search_volume))]
    allowed = {"avg_monthly_searches", "cpc", "competition", "fetched_at", "submitted_keyword"}
    key_name = criteria.sort_by if criteria.sort_by in allowed else "avg_monthly_searches"
    return sorted(items, key=lambda x: (getattr(x, key_name) is None, getattr(x, key_name) or 0), reverse=criteria.descending)


def stale_evidence_ids(evidence: list[KeywordMetricEvidence], now: datetime | None = None) -> list[str]:
    now = now or datetime.utcnow()
    return [x.id for x in evidence if x.fresh_until is not None and x.fresh_until < now]


def export_rows(evidence: list[KeywordMetricEvidence]) -> list[dict]:
    return [{"keyword": x.submitted_keyword, "provider_keyword": x.provider_keyword,
        "provider": x.provider, "location": x.location_name, "language": x.language_code,
        "country": x.country_code, "search_volume": x.avg_monthly_searches, "monthly_history": x.monthly_history or [], "cpc": x.cpc,
        "competition": x.competition, "competition_index": x.competition_index,
        "low_bid": x.low_bid, "high_bid": x.high_bid, "mapping_status": x.mapping_status,
        "fetched_at": x.fetched_at.isoformat() if x.fetched_at else None} for x in evidence]
