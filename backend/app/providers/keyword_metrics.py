"""Provider-neutral keyword metrics boundary."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.providers.contracts import KeywordMetricRequest, KeywordMetricResult
from app.providers.keyword_metrics_safety import KeywordMetricsSafetyConfig, KeywordMetricsGuardError


class KeywordMetricsProvider(Protocol):
    provider_name: str

    async def fetch(self, requests: list[KeywordMetricRequest]) -> list[KeywordMetricResult]: ...


@dataclass
class MockKeywordMetricsProvider:
    provider_name: str = "mock"
    default_volume: int = 0

    async def fetch(self, requests: list[KeywordMetricRequest]) -> list[KeywordMetricResult]:
        return [KeywordMetricResult(
            keyword=request.keyword,
            provider_keyword=request.keyword,
            avg_monthly_searches=self.default_volume,
            provider=self.provider_name,
            raw={"mock": True},
            cost=0.0,
        ) for request in requests]


@dataclass
class ImportedKeywordMetricsProvider:
    """Adapter for already-imported evidence; never performs network I/O."""
    records: dict[tuple[str, str | None, str], KeywordMetricResult]
    provider_name: str = "imported"

    async def fetch(self, requests: list[KeywordMetricRequest]) -> list[KeywordMetricResult]:
        results = []
        for request in requests:
            key = (request.keyword.strip().casefold(), request.location_name, request.language_code)
            result = self.records.get(key)
            if result is None:
                result = KeywordMetricResult(keyword=request.keyword, provider_keyword=None,
                    avg_monthly_searches=None, provider=self.provider_name,
                    raw={"mapping_status": "NOT_FOUND"}, cost=0.0)
            results.append(result)
        return results


class GoogleAdsKeywordMetricsProvider:
    """Guarded Google Ads historical-metrics adapter.

    The client is created lazily, after all safety guards pass. ``client_factory``
    is injectable so tests never need Google transport.
    """
    provider_name = "google_ads"

    def __init__(self, *, enabled: bool = False, live_approved: bool = False,
                 credentials_configured: bool = False, developer_token: str | None = None,
                 client_id: str | None = None, client_secret: str | None = None,
                 refresh_token: str | None = None, customer_id: str | None = None,
                 login_customer_id: str | None = None, client_factory=None,
                 provider_currency_code: str | None = None):
        self.enabled = enabled
        self.live_approved = live_approved
        self.credentials_configured = credentials_configured
        self.developer_token = developer_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.customer_id = customer_id
        self.login_customer_id = login_customer_id
        self.provider_currency_code = provider_currency_code
        self.client_factory = client_factory

    async def fetch(self, requests: list[KeywordMetricRequest]) -> list[KeywordMetricResult]:
        KeywordMetricsSafetyConfig(provider=self.provider_name, enabled=self.enabled,
            live_approved=self.live_approved, credentials_configured=self.credentials_configured).validate(requested_items=len(requests), estimated_cost=0.0)
        if not requests:
            return []
        if not self.customer_id:
            raise KeywordMetricsGuardError("Google Ads customer ID is not configured")
        from app.providers.google_ads_keyword_metrics import build_google_ads_request
        client = self._client()
        service = client.get_service("KeywordPlanIdeaService")
        request = build_google_ads_request(client, self.customer_id, requests)
        response = service.generate_keyword_historical_metrics(request=request, retry=None)
        from app.providers.google_ads_keyword_metrics import map_google_ads_response
        results = map_google_ads_response(response)
        for result in results:
            result.provider_currency_code = self.provider_currency_code
        return results

    def _client(self):
        if self.client_factory:
            return self.client_factory()
        from google.ads.googleads.client import GoogleAdsClient
        credentials = {
            "developer_token": self.developer_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "login_customer_id": self.login_customer_id,
            "use_proto_plus": True,
        }
        return GoogleAdsClient.load_from_dict(credentials)
