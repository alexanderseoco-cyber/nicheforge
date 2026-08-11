import asyncio
from datetime import datetime, timezone

from app.providers.location_resolution import DataForSEOLocationResolver, ResolvedLocation


def test_verified_salina_provider_location_fixture_resolves_exact_code_without_guessing():
    resolver = DataForSEOLocationResolver(type("Client", (), {})())
    resolver.cache_verified(
        ResolvedLocation("Salina,Kansas,United States", 1017623, "US", "dataforseo", datetime.now(timezone.utc)),
        "Salina", "KS",
    )
    resolved = asyncio.run(resolver.resolve("Salina", "KS"))
    assert resolved.code == 1017623
    assert resolved.name == "Salina,Kansas,United States"


def test_google_serp_us_endpoint_resolves_city_and_rejects_state_fallback():
    class Client:
        async def get(self, path):
            assert path == "/v3/serp/google/locations/us"
            return {"locations": [
                {"location_name": "Springfield,Illinois,United States", "location_code": 1,
                 "country_iso_code": "US", "location_type": "City"},
                {"location_name": "Illinois,United States", "location_code": 2,
                 "country_iso_code": "US", "location_type": "State"},
            ]}
    resolved = asyncio.run(DataForSEOLocationResolver(Client()).resolve("Springfield", "IL"))
    assert resolved.code == 1
    assert resolved.location_type == "City"
    assert resolved.source_endpoint.endswith("/us")


def test_google_serp_location_requires_country_and_city_type():
    class Client:
        async def get(self, path):
            return {"locations": [
                {"location_name": "Paris,France", "location_code": 1,
                 "country_iso_code": "FR", "location_type": "City"},
                {"location_name": "Paris,Texas,United States", "location_code": 2,
                 "country_iso_code": "US", "location_type": "State"},
            ]}
    try:
        asyncio.run(DataForSEOLocationResolver(Client()).resolve("Paris", "TX"))
    except ValueError as exc:
        assert "ambiguous or not found" in str(exc)
    else:
        raise AssertionError("state/country fallback must not resolve")
