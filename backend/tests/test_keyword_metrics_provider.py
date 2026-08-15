import pytest

from app.providers.contracts import KeywordMetricRequest
from app.providers.keyword_metrics import GoogleAdsKeywordMetricsProvider, MockKeywordMetricsProvider
from app.providers import factory
from app.services.customer_rate_limiter import CustomerRateLimiter
from app.services.operation_budget import OperationBudgetExceeded, OperationBudgetGuard


def test_factory_rejects_unknown_provider(monkeypatch):
    class Settings:
        keyword_metrics_provider = "unknown"
    monkeypatch.setattr(factory, "get_settings", lambda: Settings())
    with pytest.raises(ValueError, match="Unknown keyword metrics provider"):
        factory.keyword_metrics_provider()


@pytest.mark.asyncio
async def test_customer_rate_limiter_spaces_same_customer_but_not_other_customers():
    now = [0.0]
    waits = []

    def clock():
        return now[0]

    async def sleep(seconds):
        waits.append(seconds)
        now[0] += seconds

    limiter = CustomerRateLimiter(requests_per_second=2, enabled=True, clock=clock, sleep=sleep)
    await limiter.acquire("customer-a")
    await limiter.acquire("customer-a")
    await limiter.acquire("customer-b")
    assert len(waits) == 1 and waits[0] == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_customer_rate_limiter_disabled_is_zero_wait():
    waits = []

    async def sleep(seconds):
        waits.append(seconds)

    limiter = CustomerRateLimiter(enabled=False, sleep=sleep)
    await limiter.acquire("customer-a")
    await limiter.acquire("customer-a")
    assert waits == []


def test_operation_budget_counts_attempts_not_keywords_and_blocks_atomically():
    guard = OperationBudgetGuard(2)
    guard.reserve_attempt("customer-a")
    guard.reserve_attempt("customer-a")
    assert guard.used("customer-a") == 2
    with pytest.raises(OperationBudgetExceeded):
        guard.reserve_attempt("customer-a")
    assert guard.used("customer-a") == 2
    guard.reserve_attempt("customer-b")
    assert guard.used("customer-b") == 1


def test_operation_budget_unset_is_explicitly_unknown_and_unlimited():
    guard = OperationBudgetGuard()
    guard.reserve_attempt("customer-a", 10000)
    assert guard.status == "UNKNOWN_UNVERIFIED"


def test_operation_budget_is_rolling_24_hours(monkeypatch):
    from datetime import datetime, timedelta, timezone
    import app.services.operation_budget as budget_module
    current = [datetime(2026, 1, 2, 12, tzinfo=timezone.utc)]
    class Clock:
        @staticmethod
        def now(tz=None):
            return current[0]
    monkeypatch.setattr(budget_module, "datetime", Clock)
    guard = OperationBudgetGuard(1)
    guard.reserve_attempt("customer-a")
    current[0] += timedelta(hours=23, minutes=59)
    with pytest.raises(OperationBudgetExceeded):
        guard.reserve_attempt("customer-a")
    current[0] += timedelta(minutes=2)
    guard.reserve_attempt("customer-a")


@pytest.mark.asyncio
async def test_production_google_transport_requires_enabled_limiter_before_client():
    provider = GoogleAdsKeywordMetricsProvider(
        enabled=True, live_approved=True, credentials_configured=True,
        production_enabled=True, verified_access_level="BASIC",
        customer_id="4553815994", login_customer_id="2888497931",
    )
    with pytest.raises(RuntimeError, match="rate limiter"):
        await provider.fetch([KeywordMetricRequest("term")])


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
async def test_google_production_requires_verified_basic_or_standard_access():
    provider = GoogleAdsKeywordMetricsProvider(
        enabled=True, live_approved=True, credentials_configured=True,
        production_enabled=True, verified_access_level="UNKNOWN",
    )
    with pytest.raises(RuntimeError, match="verified BASIC or STANDARD"):
        await provider.fetch([KeywordMetricRequest("term")])


@pytest.mark.asyncio
async def test_mock_provider_returns_zero_cost_and_provider_identity():
    result = await MockKeywordMetricsProvider(default_volume=42).fetch([KeywordMetricRequest("Tree Removal")])
    assert result[0].provider_keyword == "Tree Removal"
    assert result[0].avg_monthly_searches == 42
    assert result[0].cost == 0.0


@pytest.mark.asyncio
async def test_google_v27_uses_request_object_invocation():
    class Request:
        def __init__(self):
            self.customer_id = None; self.keywords = []; self.geo_target_constants = []
            self.language = None; self.keyword_plan_network = None

    class Service:
        def __init__(self): self.request = None
        def generate_keyword_historical_metrics(self, request=None, *, retry=None):
            self.request = request
            return type("Response", (), {"results": []})()

    class Client:
        enums = type("Enums", (), {"KeywordPlanNetworkEnum": type("Network", (), {"GOOGLE_SEARCH": 1})})
        def __init__(self): self.service = Service()
        def get_type(self, name):
            if name == "GenerateKeywordHistoricalMetricsRequest": return Request()
            if name == "HistoricalMetricsOptions": return type("Options", (), {"include_average_cpc": False})()
            raise AssertionError(name)
        def get_service(self, name): assert name == "KeywordPlanIdeaService"; return self.service

    client = Client()
    provider = GoogleAdsKeywordMetricsProvider(
        enabled=True, live_approved=True, credentials_configured=True,
        customer_id="4553815994", login_customer_id="2888497931",
        client_factory=lambda: client,
    )
    await provider.fetch([KeywordMetricRequest("plumber")])
    assert client.service.request.customer_id == "4553815994"
    assert client.service.request.keywords == ["plumber"]
    assert client.service.request.historical_metrics_options.include_average_cpc is True
