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
