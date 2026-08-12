import pytest

from app.providers.contracts import KeywordMetricRequest
from app.providers.keyword_metrics import GoogleAdsKeywordMetricsProvider, MockKeywordMetricsProvider
from app.providers import factory


def test_factory_rejects_unknown_provider(monkeypatch):
    class Settings:
        keyword_metrics_provider = "unknown"
    monkeypatch.setattr(factory, "get_settings", lambda: Settings())
    with pytest.raises(ValueError, match="Unknown keyword metrics provider"):
        factory.keyword_metrics_provider()


@pytest.mark.asyncio
async def test_google_provider_blocks_disabled_before_transport():
    provider = GoogleAdsKeywordMetricsProvider(enabled=False, live_approved=True)
    with pytest.raises(RuntimeError, match="disabled"):
        await provider.fetch([KeywordMetricRequest("term")])


@pytest.mark.asyncio
async def test_google_provider_blocks_unapproved_before_transport():
    provider = GoogleAdsKeywordMetricsProvider(enabled=True, live_approved=False)
    with pytest.raises(RuntimeError, match="approval"):
        await provider.fetch([KeywordMetricRequest("term")])


@pytest.mark.asyncio
async def test_mock_provider_returns_zero_cost_and_provider_identity():
    result = await MockKeywordMetricsProvider(default_volume=42).fetch([KeywordMetricRequest("Tree Removal")])
    assert result[0].provider_keyword == "Tree Removal"
    assert result[0].avg_monthly_searches == 42
    assert result[0].cost == 0.0
