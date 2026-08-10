from app.providers.contracts import SerpRequest
from app.providers.dataforseo import DataForSEOSandboxSerpProvider
from app.providers.runtime_config import DataForSEOConfig, ProviderMode


def test_sandbox_maps_only_organic_results_and_preserves_provenance():
    response = {"tasks": [{"result": [{"items": [
        {"type": "paid", "url": "https://ad.example"},
        {"type": "organic", "rank_absolute": 3, "title": "Result", "url": "https://one.example"},
        {"type": "organic", "rank_absolute": 4, "title": "Second", "url": "https://two.example"},
    ]}]}]}
    result = DataForSEOSandboxSerpProvider.map_response(SerpRequest("term", "Austin, TX", depth=1), response)
    assert result.provider == "dataforseo_sandbox"
    assert len(result.organic) == 1
    assert result.organic[0].url == "https://one.example"
    assert result.raw["mode"] == "SANDBOX"


def test_sandbox_has_zero_cost_and_cannot_run_paid_path():
    config = DataForSEOConfig(mode=ProviderMode.SANDBOX)
    config.validate_paid_execution(0, approved=False)
    assert config.standard_serp_cost == 0
    try:
        DataForSEOConfig(mode=ProviderMode.PRODUCTION, production_enabled=True).validate_paid_execution(1, True)
    except ValueError as exc:
        assert "credentials" in str(exc)
    else:
        raise AssertionError("missing credentials must block paid execution")


def test_sandbox_smoke_transport_is_opt_in(monkeypatch):
    import asyncio
    provider = DataForSEOSandboxSerpProvider()
    monkeypatch.delenv("NICHEFORGE_ENABLE_DATAFORSEO_SANDBOX_SMOKE", raising=False)
    try:
        asyncio.run(provider.fetch([SerpRequest("term", "Austin, TX")]))
    except RuntimeError as exc:
        assert "disabled" in str(exc)
    else:
        raise AssertionError("smoke transport must be disabled by default")


def test_sandbox_default_transport_uses_sandbox_host_and_canonical_mapper(monkeypatch):
    import asyncio
    import httpx
    from app.providers.dataforseo import DataForSEOSandboxSerpProvider

    captured = {}
    real_async_client = httpx.AsyncClient
    async def handler(request):
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"tasks": [{"result": [{"items": [
            {"type": "paid", "url": "https://ad.example"},
            {"type": "organic", "rank_absolute": 2, "title": "Sample", "url": "https://sample.example"},
        ]}]}]})

    monkeypatch.setenv("NICHEFORGE_ENABLE_DATAFORSEO_SANDBOX_SMOKE", "1")
    monkeypatch.setenv("DATAFORSEO_LOGIN", "login")
    monkeypatch.setenv("DATAFORSEO_PASSWORD", "password")
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: real_async_client(transport=httpx.MockTransport(handler), **kwargs))
    result = asyncio.run(DataForSEOSandboxSerpProvider().fetch([SerpRequest("term", "Austin, TX", depth=1)]))[0]
    assert captured["url"] == "https://sandbox.dataforseo.com/v3/serp/google/organic/live/regular"
    assert captured["auth"].startswith("Basic ")
    assert len(result.organic) == 1 and result.provider == "dataforseo_sandbox"
    assert result.raw["mode"] == "SANDBOX"


def test_sandbox_http_diagnostic_redacts_credentials(monkeypatch):
    import asyncio
    import httpx
    from app.providers.dataforseo import DataForSEOSandboxSerpProvider
    async def handler(request):
        return httpx.Response(401, json={"status_code": 40203, "status_message": "Authentication failed"})
    monkeypatch.setenv("NICHEFORGE_ENABLE_DATAFORSEO_SANDBOX_SMOKE", "1")
    real_async_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: real_async_client(transport=httpx.MockTransport(handler), **kwargs))
    try:
        asyncio.run(DataForSEOSandboxSerpProvider().fetch([SerpRequest("term", "Austin, TX")]))
    except RuntimeError as exc:
        message = str(exc)
        assert "http_http_status" in message and "40203" in message
        assert "credentials_exposed=false" in message
        assert "Authorization" not in message and "login" not in message.lower()
    else:
        raise AssertionError("HTTP failure must surface a safe diagnostic")
