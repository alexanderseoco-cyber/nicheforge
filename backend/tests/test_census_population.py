import asyncio

from app.providers.census_population import CensusPopulationProvider, redact_census_url


def test_census_guards_block_transport():
    for provider, message in [(CensusPopulationProvider(None, False), "CENSUS_API_ENABLED"), (CensusPopulationProvider(None, True), "CENSUS_API_KEY")]:
        try:
            asyncio.run(provider.resolve_places("10"))
        except RuntimeError as exc:
            assert message in str(exc)
        else:
            raise AssertionError("Census transport was not blocked")


def test_census_url_redacts_key():
    url = "https://api.census.gov/data/2023/pep/population?get=NAME&key=secret"
    assert "secret" not in redact_census_url(url)
    assert "REDACTED" in redact_census_url(url)


def test_census_response_mapping(monkeypatch):
    class Response:
        def raise_for_status(self): pass
        def json(self): return [["NAME", "POP_2023", "state", "place"], ["Wilmington city, Delaware", "70000", "10", "77500"]]
    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, url):
            assert "key=secret" in url
            return Response()
    monkeypatch.setattr("app.providers.census_population.httpx.AsyncClient", lambda: Client())
    result = asyncio.run(CensusPopulationProvider("secret", True).resolve_places("10"))[0]
    assert result.population == 70000
    assert result.geoid == "1600000US1077500"
    assert result.place_fips == "77500"
