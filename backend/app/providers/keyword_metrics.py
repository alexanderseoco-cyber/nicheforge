"""Provider-neutral keyword metrics boundary.

This module deliberately contains no live transport. Provider implementations
return contracts; orchestration and persistence remain service responsibilities.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.providers.contracts import KeywordMetricRequest, KeywordMetricResult
from app.providers.keyword_metrics_safety import KeywordMetricsSafetyConfig


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
    """Transport-disabled skeleton for the optional Google Ads provider."""
    provider_name = "google_ads"

    def __init__(self, *, enabled: bool = False, live_approved: bool = False,
                 credentials_configured: bool = False):
        self.enabled = enabled
        self.live_approved = live_approved
        self.credentials_configured = credentials_configured

    async def fetch(self, requests: list[KeywordMetricRequest]) -> list[KeywordMetricResult]:
        KeywordMetricsSafetyConfig(provider=self.provider_name, enabled=self.enabled,
            live_approved=self.live_approved, credentials_configured=self.credentials_configured).validate(requested_items=len(requests), estimated_cost=0.0)
        raise NotImplementedError("Google Ads transport is not implemented; no network request was made")
