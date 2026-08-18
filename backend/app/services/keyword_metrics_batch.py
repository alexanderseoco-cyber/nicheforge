"""Cache-first orchestration contract for the Keyword Metrics Engine."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
import hashlib

from app.models.entities import ProviderCall
from app.services.operation_budget import OperationBudgetExceeded
from app.services.provider_call_telemetry import safe_create_provider_call, safe_update_provider_call

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
                 chunk_size: int = 10_000, db=None, customer_id: str | None = None):
        self.provider = provider
        self.cache = cache if cache is not None else {}
        self.completed = completed if completed is not None else {}
        self.chunk_size = max(1, chunk_size)
        self.db = db
        self.customer_id = customer_id

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
        stale_count = 0
        for key, request in unique.items():
            if key in self.completed:
                result.results[request.keyword] = self.completed[key]; result.mapping_status[request.keyword] = "RESUMED"; result.resumed = True
            elif key in self.cache and self.cache[key].fresh:
                result.results[request.keyword] = self.cache[key].result; result.mapping_status[request.keyword] = "CACHE_HIT"; result.cache_hits += 1
            else:
                if key in self.cache:
                    stale_count += 1
                pending.append(request)
        if self.db is not None and (result.cache_hits or result.resumed):
            provider_name = getattr(self.provider, "provider_name", "unknown")
            reuse_call = safe_create_provider_call(self.db, lambda: ProviderCall(
                provider=provider_name, execution_mode="LIVE" if getattr(self.provider, "is_live_transport", False) else "MOCK",
                stage="keyword_metrics", operation="CACHE_REUSE", request_cache_key="keyword-metrics-reuse:" + hashlib.sha256(
                    json.dumps(sorted(self._key(item) for item in requests), default=str, sort_keys=True).encode("utf-8")
                ).hexdigest(),
                outcome="CACHE_HIT", cache_hit=True, source_kind="cache", started_at=datetime.utcnow(),
                estimated_cost=None, actual_cost=None, currency=None,
                logical_item_count=len(requests), unique_target_count=len(unique),
                cache_hit_count=result.cache_hits, cache_miss_count=len(pending), stale_count=stale_count,
                cache_outcome="HIT", cache_provider_dimension=provider_name,
                actual_evidence_provider=provider_name, evidence_reused_count=result.cache_hits,
                evidence_created_count=0, evidence_partial_count=0, evidence_missing_count=0,
                provider_item_count=0, batch_size=0, batch_count=0, http_request_count=0,
                http_request_sent=False, paid_attempt=False, retry_count=0, cost_confidence="NOT_APPLICABLE",
            ))
        if not pending:
            return result
        for start in range(0, len(pending), self.chunk_size):
            chunk = pending[start:start + self.chunk_size]
            provider_call = None
            if self.db is not None:
                provider_name = getattr(self.provider, "provider_name", "unknown")
                live_transport = bool(getattr(self.provider, "is_live_transport", False))
                target = chunk[0].location_name if chunk else None
                provider_call = safe_create_provider_call(self.db, lambda: ProviderCall(
                    provider=provider_name,
                    execution_mode="LIVE" if live_transport else "MOCK",
                    stage="keyword_metrics",
                    operation="generate_keyword_historical_metrics",
                    request_cache_key="keyword-metrics:" + hashlib.sha256(
                        json.dumps([self._key(item) for item in chunk], default=str, sort_keys=True).encode("utf-8")
                    ).hexdigest(),
                    outcome="STARTED",
                    source_kind="live_api" if live_transport else "mock",
                    started_at=datetime.utcnow(),
                    estimated_cost=0.0,
                    currency=None,
                    customer_id=self.customer_id,
                    target_identity=target,
                    language_code=chunk[0].language_code if chunk else None,
                    chunk_index=(start // self.chunk_size) + 1,
                    chunk_count=(len(pending) + self.chunk_size - 1) // self.chunk_size,
                    submitted_keyword_count=len(chunk),
                    attempt_number=1,
                    logical_item_count=len(chunk),
                    unique_target_count=len({self._key(item) for item in chunk}),
                    cache_hit_count=0,
                    cache_miss_count=len(chunk),
                    stale_count=0,
                    cache_outcome="MISS",
                    cache_provider_dimension=provider_name,
                    provider_item_count=len(chunk),
                    batch_size=len(chunk),
                    batch_count=1,
                    http_request_count=1 if live_transport else 0,
                    http_request_sent=live_transport,
                    paid_attempt=None,
                    retry_count=0,
                    cost_confidence="UNKNOWN",
                ))
            try:
                returned = await self.provider.fetch(chunk)
                if provider_call is not None:
                    finished_at = datetime.utcnow()
                    safe_update_provider_call(self.db, provider_call,
                        finished_at=finished_at,
                        duration_ms=(finished_at - provider_call.started_at).total_seconds() * 1000,
                        outcome="SUCCESS",
                        provider_reached=bool(getattr(self.provider, "is_live_transport", False)),
                        operation_count=1 if getattr(self.provider, "is_live_transport", False) else 0,
                        actual_cost=None,
                        items_returned_count=sum(1 for item in returned if item is not None and not (isinstance(item.raw, dict) and item.raw.get("mapping_status") == "NOT_FOUND")),
                        items_failed_count=max(0, len(chunk) - sum(1 for item in returned if item is not None and not (isinstance(item.raw, dict) and item.raw.get("mapping_status") == "NOT_FOUND"))))
            except Exception as exc:
                if provider_call is not None:
                    finished_at = datetime.utcnow()
                    outcome = "BUDGET_EXCEEDED" if isinstance(exc, OperationBudgetExceeded) else ("PROVIDER_REJECTED" if type(exc).__name__ == "GoogleAdsException" else "NETWORK_FAILURE_BEFORE_PROVIDER")
                    safe_update_provider_call(self.db, provider_call,
                        finished_at=finished_at,
                        duration_ms=(finished_at - provider_call.started_at).total_seconds() * 1000,
                        outcome=outcome,
                        provider_reached=outcome == "PROVIDER_REJECTED",
                        operation_count=1 if outcome == "PROVIDER_REJECTED" else 0,
                        error_category=type(exc).__name__,
                        error_message=f"{type(exc).__name__}: {str(exc)[:500]}",
                        items_returned_count=0,
                        items_failed_count=len(chunk),
                        actual_cost=None)
                raise
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
