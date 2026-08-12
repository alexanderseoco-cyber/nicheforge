from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.providers.contracts import KeywordMetricRequest, KeywordMetricResult


@dataclass(frozen=True)
class GoogleAdsHistoricalMetricsRequest:
    customer_id: str
    keywords: list[str]
    geo_target_constants: list[str]
    language: str | None
    keyword_plan_network: str = "GOOGLE_SEARCH"
    include_average_cpc: bool = True

    def as_payload(self) -> dict[str, Any]:
        return {"customer_id": self.customer_id, "keywords": self.keywords,
            "geo_target_constants": self.geo_target_constants, "language": self.language,
            "keyword_plan_network": self.keyword_plan_network,
            "historical_metrics_options": {"include_average_cpc": self.include_average_cpc}}


def language_resource(language_code: str) -> str:
    known = {"en": "customers/-/languageConstants/1000"}
    return known.get(language_code.casefold(), f"customers/-/languageConstants/{language_code}")


def geo_resource(geo_id: str) -> str:
    return geo_id if geo_id.startswith("customers/") else f"customers/-/geoTargetConstants/{geo_id}"


def build_historical_metrics_request(customer_id: str, requests: list[KeywordMetricRequest]) -> GoogleAdsHistoricalMetricsRequest:
    if not requests:
        raise ValueError("At least one keyword is required")
    first = requests[0]
    geo_ids = list((first.location_target or {}).get("geo_target_ids", []))
    if len(geo_ids) > 10:
        raise ValueError("Google Ads supports at most 10 geo targets per request")
    return GoogleAdsHistoricalMetricsRequest(customer_id=customer_id,
        keywords=[r.keyword for r in requests], geo_target_constants=[geo_resource(x) for x in geo_ids],
        language=language_resource(first.language_code))


def map_historical_metrics_response(payload: dict[str, Any]) -> list[KeywordMetricResult]:
    def micros(value):
        return value / 1_000_000 if value is not None else None
    results = []
    for item in payload.get("results", []):
        metrics = item.get("keyword_metrics") or {}
        results.append(KeywordMetricResult(keyword=item.get("text", ""), provider_keyword=item.get("text"),
            avg_monthly_searches=metrics.get("avg_monthly_searches"),
            cpc=micros(metrics.get("average_cpc_micros")),
            competition=metrics.get("competition"), competition_index=metrics.get("competition_index"),
            low_bid=micros(metrics.get("low_top_of_page_bid_micros")),
            high_bid=micros(metrics.get("high_top_of_page_bid_micros")),
            monthly_history=metrics.get("monthly_search_volumes", []), provider="google_ads",
            raw={"close_variants": item.get("close_variants", [])}, cost=0.0))
    return results
