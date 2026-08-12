from app.services.keyword_metrics_identity import keyword_metric_cache_key, normalize_metric_keyword


def test_keyword_normalization_is_deterministic():
    assert normalize_metric_keyword("  Tree   Removal Service ") == "tree removal service"


def test_geo_targeted_and_embedded_location_are_distinct():
    targeted = keyword_metric_cache_key(keyword="tree removal service", location_name="Youngstown, Ohio", location_target={"geo_id": "x"}, language_code="en", country_code="US", provider="google_ads")
    embedded = keyword_metric_cache_key(keyword="tree removal service youngstown oh", location_name="United States", location_target={"country": "US"}, language_code="en", country_code="US", provider="google_ads")
    assert targeted != embedded


def test_provider_and_version_are_part_of_identity():
    base = dict(keyword="term", location_name=None, location_target={}, language_code="en", country_code="US")
    assert keyword_metric_cache_key(**base, provider="mock") != keyword_metric_cache_key(**base, provider="google_ads")
    assert keyword_metric_cache_key(**base, provider="mock", metric_version="v1") != keyword_metric_cache_key(**base, provider="mock", metric_version="v2")
