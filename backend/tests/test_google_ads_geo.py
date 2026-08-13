import pytest
from app.providers.google_ads_geo import GoogleAdsGeoTargetResolver, GeoResolutionError


class FakeClient:
    def __init__(self, suggestions): self.suggestions = suggestions; self.service = self
    def get_service(self, name): assert name == "GeoTargetConstantService"; return self
    def get_type(self, name):
        class Names: names = []
        class Request: locale = None; country_code = None; location_names = Names()
        return Request()
    def suggest_geo_target_constants(self, request):
        return type("Response", (), {"geo_target_constant_suggestions": self.suggestions})()


def suggestion(name="Albany", canonical="Albany,Georgia,United States", country="US", target_type="CITY", resource="geoTargetConstants/123"):
    target = type("Target", (), {"name": name, "canonical_name": canonical, "country_code": country, "target_type": target_type, "resource_name": resource, "status": "ENABLED"})()
    return type("Suggestion", (), {"geo_target_constant": target})()


@pytest.mark.asyncio
async def test_albany_ga_exact_match_and_cache_reuse():
    client = FakeClient([suggestion()])
    resolver = GoogleAdsGeoTargetResolver(client_factory=lambda: client, enabled=True, live_approved=True, credentials_configured=True)
    result = await resolver.resolve("Albany", "Georgia")
    assert result.resource_name == "geoTargetConstants/123"
    await resolver.resolve("Albany", "Georgia")
    assert resolver.network_calls == 1


@pytest.mark.asyncio
async def test_wrong_country_or_state_is_not_accepted():
    resolver = GoogleAdsGeoTargetResolver(client_factory=lambda: FakeClient([suggestion(country="CA")]), enabled=True, live_approved=True, credentials_configured=True)
    with pytest.raises(GeoResolutionError, match="NOT_FOUND"):
        await resolver.resolve("Albany", "Georgia")


@pytest.mark.asyncio
async def test_ambiguous_match_is_explicit():
    resolver = GoogleAdsGeoTargetResolver(client_factory=lambda: FakeClient([suggestion(resource="geoTargetConstants/1"), suggestion(resource="geoTargetConstants/2")]), enabled=True, live_approved=True, credentials_configured=True)
    with pytest.raises(GeoResolutionError, match="AMBIGUOUS"):
        await resolver.resolve("Albany", "Georgia")


@pytest.mark.asyncio
async def test_disabled_blocks_before_transport():
    resolver = GoogleAdsGeoTargetResolver(client_factory=lambda: (_ for _ in ()).throw(AssertionError("transport")))
    with pytest.raises(PermissionError):
        await resolver.resolve("Albany", "Georgia")
