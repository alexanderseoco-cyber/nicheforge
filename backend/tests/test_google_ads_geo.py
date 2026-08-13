import pytest
from app.providers.google_ads_geo import GoogleAdsGeoTargetResolver, GeoResolutionError, GeoTransportError, classify_transport_exception, normalize_us_state


class FakeClient:
    def __init__(self, suggestions): self.suggestions = suggestions; self.service = self
    def get_service(self, name): assert name == "GeoTargetConstantService"; return self
    def get_type(self, name):
        class Names: names = []
        class Request: locale = None; country_code = None; location_names = Names()
        return Request()
    def suggest_geo_target_constants(self, request):
        return type("Response", (), {"geo_target_constant_suggestions": self.suggestions})()


class FailingClient(FakeClient):
    def suggest_geo_target_constants(self, request):
        raise RuntimeError("TransportError: gRPC unavailable")


def suggestion(name="Albany", canonical="Albany,Georgia,United States", country="US", target_type="CITY", resource="geoTargetConstants/123"):
    target = type("Target", (), {"name": name, "canonical_name": canonical, "country_code": country, "target_type": target_type, "resource_name": resource, "status": "ENABLED"})()
    return type("Suggestion", (), {"geo_target_constant": target})()

def test_all_us_state_abbreviations_and_names_normalize():
    assert normalize_us_state("MO") == "MO"
    assert normalize_us_state("Missouri") == "MO"
    assert normalize_us_state("GA") == "GA"
    assert normalize_us_state("Georgia") == "GA"
    assert normalize_us_state("invalid") == ""

@pytest.mark.asyncio
@pytest.mark.parametrize("city,state,canonical", [
    ("Cape Girardeau", "MO", "Cape Girardeau,Missouri,United States"),
    ("Cape Girardeau", "Missouri", "Cape Girardeau,Missouri,United States"),
    ("Warner Robins", "GA", "Warner Robins,Georgia,United States"),
    ("Albany", "GA", "Albany,Georgia,United States"),
    ("Rochester", "MN", "Rochester,Minnesota,United States"),
])
async def test_state_name_and_abbreviation_accept_exact_city(city, state, canonical):
    resolver = GoogleAdsGeoTargetResolver(client_factory=lambda: FakeClient([suggestion(city, canonical)]), enabled=True, live_approved=True, credentials_configured=True)
    result = await resolver.resolve(city, state)
    assert result.city == city

@pytest.mark.asyncio
@pytest.mark.parametrize("city,state,canonical", [
    ("Albany", "GA", "Albany,New York,United States"),
    ("Rochester", "MN", "Rochester,New York,United States"),
])
async def test_same_name_wrong_state_rejected(city, state, canonical):
    resolver = GoogleAdsGeoTargetResolver(client_factory=lambda: FakeClient([suggestion(city, canonical)]), enabled=True, live_approved=True, credentials_configured=True)
    with pytest.raises(GeoResolutionError, match="NOT_FOUND"):
        await resolver.resolve(city, state)


@pytest.mark.asyncio
async def test_albany_ga_exact_match_and_cache_reuse():
    client = FakeClient([suggestion()])
    resolver = GoogleAdsGeoTargetResolver(client_factory=lambda: client, enabled=True, live_approved=True, credentials_configured=True)
    result = await resolver.resolve("Albany", "Georgia")
    assert result.resource_name == "geoTargetConstants/123"
    await resolver.resolve("Albany", "Georgia")
    assert resolver.network_calls == 1
    assert resolver.network_attempts == 1 and resolver.network_successes == 1 and resolver.network_failures == 0


@pytest.mark.asyncio
async def test_transport_failure_counts_attempt_and_failure():
    resolver = GoogleAdsGeoTargetResolver(client_factory=lambda: FailingClient([]), enabled=True, live_approved=True, credentials_configured=True)
    with pytest.raises(RuntimeError):
        await resolver.resolve("Albany", "Georgia")
    assert resolver.network_attempts == 1 and resolver.network_successes == 0 and resolver.network_failures == 1


@pytest.mark.asyncio
async def test_cache_and_guard_do_not_count_attempts():
    client = FakeClient([suggestion()])
    resolver = GoogleAdsGeoTargetResolver(client_factory=lambda: client, enabled=True, live_approved=True, credentials_configured=True)
    await resolver.resolve("Albany", "Georgia")
    await resolver.resolve("Albany", "Georgia")
    assert resolver.network_attempts == 1
    blocked = GoogleAdsGeoTargetResolver(client_factory=lambda: client)
    with pytest.raises(PermissionError):
        await blocked.resolve("Dothan", "Alabama")
    assert blocked.network_attempts == 0


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


def test_transport_diagnostics_are_stable_and_sanitized():
    assert classify_transport_exception(RuntimeError("gRPC unavailable")) == "grpc_unavailable"
    assert classify_transport_exception(RuntimeError("TLS certificate failure")) == "tls"
    error = GeoTransportError("dns_network", RuntimeError("secret-token-redacted"))
    assert error.category == "dns_network"
    assert "secret-token" not in str(error)
