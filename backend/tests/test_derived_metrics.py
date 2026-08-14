from app.services.derived_metrics import calculate_derived_metrics

def test_commercial_and_projected_value():
    result = calculate_derived_metrics(1000, 10.0, ctr_model={1: 0.25}, ctr_model_version="test-v1")
    assert result.commercial_search_value == 10000
    assert result.projected["1"]["clicks"] == 250
    assert result.projected["1"]["traffic_value"] == 2500
    assert result.ctr_model_version == "test-v1"

def test_derived_null_and_zero_semantics():
    assert calculate_derived_metrics(None, 10).commercial_search_value is None
    assert calculate_derived_metrics(0, 10).commercial_search_value == 0
    result = calculate_derived_metrics(1000, None)
    assert result.commercial_search_value is None
    assert result.projected["1"]["clicks"] == 280
    assert result.projected["1"]["traffic_value"] is None
