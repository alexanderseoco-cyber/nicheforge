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
