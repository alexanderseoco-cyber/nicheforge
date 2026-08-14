"""Cache-first orchestration contract for the Keyword Metrics Engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json

from app.providers.contracts import KeywordMetricRequest, KeywordMetricResult


@dataclass
class CachedMetric:
    result: KeywordMetricResult
    fresh: bool = True


@dataclass
class KeywordMetricsBatchResult:
    results: dict[str, KeywordMetricResult] = field(default_factory=dict)
    mapping_status: dict[str, str] = field(default_factory=dict)
    cache_hits: int = 0
    provider_requests: int = 0
    submitted_count: int = 0
    deduplicated_count: int = 0
    unmapped_count: int = 0
    resumed: bool = False
    actual_cost: float | None = 0.0
    chunks: int = 0


class KeywordMetricsBatchOrchestrator:
    """Provider-agnostic cache-first batch coordinator.

    Persistence adapters can store each returned result append-only. The
    completed-key set makes retry/resume idempotent without another transport
    call for already mapped evidence.
    """

    def __init__(self, provider, cache: dict[tuple[str, str | None, str], CachedMetric] | None = None,
                 completed: dict[tuple[str, str | None, str], KeywordMetricResult] | None = None,
                 chunk_size: int = 10_000):
        self.provider = provider
        self.cache = cache if cache is not None else {}
        self.completed = completed if completed is not None else {}
        self.chunk_size = max(1, chunk_size)

    @staticmethod
    def _key(request: KeywordMetricRequest):
        target = json.dumps(request.location_target or {}, sort_keys=True, separators=(",", ":"))
        return (request.keyword.strip().casefold(), request.location_name, request.language_code,
                request.country_code.upper(), target)

    async def execute(self, requests: list[KeywordMetricRequest]) -> KeywordMetricsBatchResult:
        unique = {}
        for request in requests:
            unique.setdefault(self._key(request), request)
        result = KeywordMetricsBatchResult(submitted_count=len(requests), deduplicated_count=len(unique))
        pending = []
        for key, request in unique.items():
            if key in self.completed:
                result.results[request.keyword] = self.completed[key]; result.mapping_status[request.keyword] = "RESUMED"; result.resumed = True
            elif key in self.cache and self.cache[key].fresh:
                result.results[request.keyword] = self.cache[key].result; result.mapping_status[request.keyword] = "CACHE_HIT"; result.cache_hits += 1
            else:
                pending.append(request)
        if not pending:
            return result
        for start in range(0, len(pending), self.chunk_size):
            chunk = pending[start:start + self.chunk_size]
            returned = await self.provider.fetch(chunk)
            result.provider_requests += 1; result.chunks += 1
            costs = [item.cost for item in returned if item.cost is not None]
            if costs: result.actual_cost = (result.actual_cost or 0.0) + sum(costs)
            by_keyword = {item.provider_keyword or item.keyword: item for item in returned}
            for request in chunk:
                item = by_keyword.get(request.keyword)
                if item is None or (isinstance(item.raw, dict) and item.raw.get("mapping_status") == "NOT_FOUND"):
                    result.results[request.keyword] = KeywordMetricResult(
                        keyword=request.keyword,
                        provider_keyword=None,
                        avg_monthly_searches=None,
                        provider=getattr(self.provider, "provider_name", "provider"),
                        raw={"mapping_status": "UNMAPPED"},
                        cost=0.0,
                    )
                    result.mapping_status[request.keyword] = "UNMAPPED"
                    result.unmapped_count += 1
                    continue
                result.results[request.keyword] = item
                result.mapping_status[request.keyword] = "MAPPED"
                self.completed[self._key(request)] = item
        return result
