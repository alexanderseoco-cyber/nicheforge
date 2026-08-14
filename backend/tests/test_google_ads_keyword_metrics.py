import pytest
from app.providers.contracts import KeywordMetricRequest
from app.providers.google_ads_keyword_metrics import build_google_ads_request, build_historical_metrics_request, map_historical_metrics_response
from app.providers.google_country_registry import country_capability


def test_google_request_maps_geo_and_language_resources():
    request=build_historical_metrics_request("123", [KeywordMetricRequest("tree removal", language_code="en", location_target={"geo_target_ids":["2840"]})])
    assert request.language == "languageConstants/1000"
    assert request.geo_target_constants == ["geoTargetConstants/2840"]
    assert "customers/" not in request.language
    assert "customers/" not in request.geo_target_constants[0]
    assert request.as_payload()["historical_metrics_options"]["include_average_cpc"] is True


def test_google_request_rejects_more_than_ten_geos():
    with pytest.raises(ValueError, match="10 geo"):
        build_historical_metrics_request("123", [KeywordMetricRequest("term", location_target={"geo_target_ids":[str(x) for x in range(11)]})])


def test_real_google_client_builder_maps_country_target():
    class Names:
        def __init__(self): self.items = []
        def extend(self, values): self.items.extend(values)
    class Request:
        def __init__(self): self.geo_target_constants = Names(); self.keywords = Names()
    class Options: pass
    class Client:
        def get_type(self, name): return Options() if name == "HistoricalMetricsOptions" else Request()
        class enums:
            class KeywordPlanNetworkEnum: GOOGLE_SEARCH = "GOOGLE_SEARCH"
    request = build_google_ads_request(Client(), "123", [KeywordMetricRequest("term", country_code="PK", location_target={"country_code": "PK"})])
    assert request.geo_target_constants.items == ["geoTargetConstants/2586"]


@pytest.mark.parametrize("country,resource", [("US", "geoTargetConstants/2840"), ("GB", "geoTargetConstants/2826"), ("PK", "geoTargetConstants/2586")])
def test_google_country_target_is_resolved_from_country_code(country, resource):
    request = build_historical_metrics_request("123", [KeywordMetricRequest("term", country_code=country, location_target={"country_code": country})])
    assert request.geo_target_constants == [resource]


def test_worldwide_is_the_only_explicit_empty_geo_target():
    request = build_historical_metrics_request("123", [KeywordMetricRequest("term", country_code="WORLD", location_target={"target_type": "WORLDWIDE", "country_code": "WORLD"})])
    assert request.geo_target_constants == []


def test_unsupported_country_is_explicitly_unsupported():
    assert country_capability("DE").status == "UNSUPPORTED"
    with pytest.raises(ValueError):
        build_historical_metrics_request("123", [KeywordMetricRequest("term", country_code="DE", location_target={"country_code": "DE"})])


def test_google_response_maps_identity_metrics_bids_history_and_variants():
    results=map_historical_metrics_response({"results":[{"text":"cars", "close_variants":["car"], "keyword_metrics":{"avg_monthly_searches":100, "competition_index":55, "average_cpc_micros":2500000, "low_top_of_page_bid_micros":1000000, "high_top_of_page_bid_micros":3000000, "monthly_search_volumes":[{"year":2026,"month":"AUGUST","monthly_searches":100}]}}]})
    assert results[0].provider_keyword=="cars" and results[0].cpc==2.5 and results[0].low_bid==1.0 and results[0].high_bid==3.0
    assert results[0].raw["close_variants"] == ["car"]


def test_google_missing_optional_fields_remain_null():
    result=map_historical_metrics_response({"results":[{"text":"term", "keyword_metrics":{}}]})[0]
    assert result.cpc is None and result.low_bid is None and result.high_bid is None
    assert result.competition is None and result.competition_index is None and result.monthly_history == []


def test_monthly_history_preserves_zero_and_sorts_enum_months_across_years():
    result = map_historical_metrics_response({"results": [{"text": "tree removal service", "keyword_metrics": {"avg_monthly_searches": 10, "monthly_search_volumes": [
        {"year": 2026, "month": "JANUARY", "monthly_searches": 0},
        {"year": 2025, "month": "DECEMBER", "monthly_searches": 7},
        {"year": 2026, "month": "FEBRUARY", "monthly_searches": 3},
    ]}}]})[0]
    assert result.monthly_history == [
        {"year": 2025, "month": 12, "searches": 7},
        {"year": 2026, "month": 1, "searches": 0},
        {"year": 2026, "month": 2, "searches": 3},
    ]


def test_google_response_adapter_does_not_drop_already_normalized_history():
    result = map_historical_metrics_response({"results": [{"text": "fancy text generator", "keyword_metrics": {
        "avg_monthly_searches": 74000,
        "monthly_search_volumes": [{"year": 2025, "month": 9, "searches": 74000}, {"year": 2026, "month": 8, "searches": 74000}],
    }}]})[0]
    assert result.monthly_history == [
        {"year": 2025, "month": 9, "searches": 74000},
        {"year": 2026, "month": 8, "searches": 74000},
    ]
