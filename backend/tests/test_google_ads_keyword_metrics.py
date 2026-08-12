import pytest
from app.providers.contracts import KeywordMetricRequest
from app.providers.google_ads_keyword_metrics import build_historical_metrics_request, map_historical_metrics_response


def test_google_request_maps_geo_and_language_resources():
    request=build_historical_metrics_request("123", [KeywordMetricRequest("tree removal", language_code="en", location_target={"geo_target_ids":["2840"]})])
    assert request.language.endswith("1000") and request.geo_target_constants == ["customers/-/geoTargetConstants/2840"]
    assert request.as_payload()["historical_metrics_options"]["include_average_cpc"] is True


def test_google_request_rejects_more_than_ten_geos():
    with pytest.raises(ValueError, match="10 geo"):
        build_historical_metrics_request("123", [KeywordMetricRequest("term", location_target={"geo_target_ids":[str(x) for x in range(11)]})])


def test_google_response_maps_identity_metrics_bids_history_and_variants():
    results=map_historical_metrics_response({"results":[{"text":"cars", "close_variants":["car"], "keyword_metrics":{"avg_monthly_searches":100, "competition_index":55, "average_cpc_micros":2500000, "low_top_of_page_bid_micros":1000000, "high_top_of_page_bid_micros":3000000, "monthly_search_volumes":[{"year":2026,"month":"AUGUST","monthly_searches":100}]}}]})
    assert results[0].provider_keyword=="cars" and results[0].cpc==2.5 and results[0].low_bid==1.0 and results[0].high_bid==3.0
    assert results[0].raw["close_variants"] == ["car"]


def test_google_missing_optional_fields_remain_null():
    result=map_historical_metrics_response({"results":[{"text":"term", "keyword_metrics":{}}]})[0]
    assert result.cpc is None and result.low_bid is None and result.high_bid is None
    assert result.competition is None and result.competition_index is None and result.monthly_history == []
