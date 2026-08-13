from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.providers.contracts import KeywordMetricRequest, KeywordMetricResult


def normalize_monthly_history(values) -> list[dict]:
    """Return provider-neutral, oldest-to-newest monthly search values."""
    normalized = []
    for value in values or []:
        year = value.get("year") if isinstance(value, dict) else getattr(value, "year", None)
        month = value.get("month") if isinstance(value, dict) else getattr(value, "month", None)
        searches = value.get("monthly_searches") if isinstance(value, dict) else getattr(value, "monthly_searches", None)
        if year is None or month is None or searches is None:
            continue
        if hasattr(month, "name"):
            month = month.name
        if isinstance(month, str) and not month.isdigit():
            month = {name: index for index, name in enumerate(("UNSPECIFIED", "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"))}.get(month.upper())
        if month is None:
            continue
        normalized.append({"year": int(year), "month": int(month), "searches": int(searches)})
    return sorted(normalized, key=lambda item: (item["year"], item["month"]))


def build_google_ads_request(client, customer_id: str, requests: list[KeywordMetricRequest]):
    """Build the official client request; no transport occurs here."""
    first = requests[0]
    request = client.get_type("GenerateKeywordHistoricalMetricsRequest")
    request.customer_id = customer_id
    request.keywords.extend([item.keyword for item in requests])
    request.geo_target_constants.extend(
        geo_resource(x) for x in list((first.location_target or {}).get("geo_target_ids", []))
    )
    request.language = language_resource(first.language_code)
    request.keyword_plan_network = client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
    return request


def map_google_ads_response(response) -> list[KeywordMetricResult]:
    payload = {"results": []}
    for item in getattr(response, "results", []):
        metrics = getattr(item, "keyword_metrics", None)
        metric_payload = {}
        if metrics is not None:
            for source, target in {
                "avg_monthly_searches": "avg_monthly_searches",
                "average_cpc_micros": "average_cpc_micros",
                "competition": "competition",
                "competition_index": "competition_index",
                "low_top_of_page_bid_micros": "low_top_of_page_bid_micros",
                "high_top_of_page_bid_micros": "high_top_of_page_bid_micros",
                "monthly_search_volumes": "monthly_search_volumes",
            }.items():
                value = getattr(metrics, source, None)
                if value is not None:
                    if target == "monthly_search_volumes":
                        value = normalize_monthly_history(value)
                    metric_payload[target] = value
        payload["results"].append({
            "text": getattr(item, "text", ""),
            "keyword_metrics": metric_payload,
            "close_variants": list(getattr(item, "close_variants", [])),
        })
    return map_historical_metrics_response(payload)


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
    known = {"en": "1000"}
    return f"languageConstants/{known.get(language_code.casefold(), language_code)}"


def geo_resource(geo_id: str) -> str:
    criterion_id = geo_id.rsplit("/", 1)[-1]
    return f"geoTargetConstants/{criterion_id}"


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
            monthly_history=normalize_monthly_history(metrics.get("monthly_search_volumes", [])), provider="google_ads",
            raw={"close_variants": item.get("close_variants", [])}, cost=0.0))
    return results
