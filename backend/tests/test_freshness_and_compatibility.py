from datetime import datetime, timedelta

from app.domain.freshness import FreshnessPolicy, can_reuse
from app.services.evidence_compatibility import authority_compatible, search_volume_compatible, serp_compatible


class Obj:
    pass


def test_freshness_policy_modes():
    assert can_reuse(FreshnessPolicy.REUSE_FRESH_ONLY, True) == (True, False)
    assert can_reuse(FreshnessPolicy.REUSE_FRESH_ONLY, False) == (False, True)
    assert can_reuse(FreshnessPolicy.ALLOW_STALE_WITH_WARNING, False) == (True, True)
    assert can_reuse(FreshnessPolicy.FORCE_REFRESH, True) == (False, False)


def test_evidence_compatibility_rejects_request_dimension_changes():
    sv = Obj(); sv.keyword="k"; sv.location_name="A"; sv.language_code="en"; sv.country_code="US"; sv.provider="mock"
    assert search_volume_compatible(sv, keyword="k", location_name="A", language_code="en", country_code="US", provider="mock")
    assert not search_volume_compatible(sv, keyword="k", location_name="B", language_code="en", country_code="US", provider="mock")
    assert not search_volume_compatible(sv, keyword="k", location_name="A", language_code="es", country_code="US", provider="mock")
    assert not search_volume_compatible(sv, keyword="k", location_name="A", language_code="en", country_code="US", provider="other")
    serp = Obj(); serp.keyword="k"; serp.location_name="A"; serp.language_code="en"; serp.country_code="US"; serp.device_profile="desktop"; serp.requested_depth=10; serp.provider="mock"
    assert serp_compatible(serp, keyword="k", location_name="A", language_code="en", country_code="US", depth=5, provider="mock")
    assert not serp_compatible(serp, keyword="k", location_name="A", language_code="en", country_code="US", depth=5, provider="mock", device_profile="mobile")
    auth = Obj(); auth.target_url="https://a.test/x"; auth.root_domain="a.test"; auth.target_type="URL"; auth.provider="mock"
    assert authority_compatible(auth, target_url="https://a.test/x", root_domain="a.test", provider="mock")
    assert not authority_compatible(auth, target_url="https://a.test/y", root_domain="a.test", provider="mock")
    assert not authority_compatible(auth, target_url="https://a.test/x", root_domain="a.test", target_type="DOMAIN", provider="mock")
