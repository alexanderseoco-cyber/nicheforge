"""Keep the test suite provider-free regardless of the developer .env file."""

import pytest
from pathlib import Path


@pytest.fixture(autouse=True)
def isolate_provider_configuration(monkeypatch, request):
    monkeypatch.setenv("NICHEFORGE_SV_PROVIDER", "mock")
    monkeypatch.setenv("NICHEFORGE_SERP_PROVIDER", "mock")
    monkeypatch.setenv("NICHEFORGE_AUTHORITY_PROVIDER", "mock")
    monkeypatch.setenv("KEYWORD_METRICS_PROVIDER", "mock")
    monkeypatch.setenv("AHREFS_PROXY_ENABLED", "false")
    monkeypatch.setenv("AHREFS_LIVE_APPROVED", "false")
    monkeypatch.setenv("DATAFORSEO_BACKLINK_PROXY_ENABLED", "false")
    monkeypatch.setenv("DATAFORSEO_BACKLINK_LIVE_APPROVED", "false")
    monkeypatch.setenv("NICHEFORGE_SINGLE_USER_MODE", "false")
    from app.core.config import get_settings
    get_settings.cache_clear()
    if request.node.name == "test_auth_migration_upgrade_on_isolated_database":
        monkeypatch.chdir(Path(__file__).resolve().parents[1])
    yield
    get_settings.cache_clear()
