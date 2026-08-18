"""Persistent, restart-safe orchestration for keyword x structured-city research."""
from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.models.entities import KeywordMetricBatch, KeywordMetricBatchItem, KeywordMetricEvidence, KeywordMetricQuery, ProviderCall, ProviderGeoMapping, ProviderCustomerMetadata, uid
from app.providers.contracts import KeywordMetricRequest
from app.services.keyword_metrics_batch import KeywordMetricsBatchOrchestrator
from app.services.currency_normalization import normalize_to_usd
from app.services.customer_currency import resolve_cached_customer_currency
from app.services.monetary_enrichment import resolve_usd_metrics
from app.services.fx_evidence import resolve_persisted_fx
from app.services.operation_budget import OperationBudgetExceeded
from app.services.provider_call_telemetry import safe_create_provider_call, safe_update_provider_call


class SystemicProviderFailure(BaseException):
    """Internal control-flow signal: stop provider work, preserve batch state."""
    def __init__(self, signature: str):
        self.signature = signature


def failure_signature(provider: str, stage: str, exc: BaseException) -> str:
    category = type(exc).__name__.casefold()
    message = str(exc).casefold()
    if any(token in message for token in ("not_found", "ambiguous")):
        return f"item:{provider}:{stage}:{category}:{message[:120]}"
    return f"systemic:{provider}:{stage}:{category}:{message[:160]}"


def is_systemic_failure(provider: str, stage: str, exc: BaseException) -> bool:
    message = str(exc).casefold()
    if "not_found" in message or "ambiguous" in message:
        return False
    return type(exc).__name__ in {"TransportError", "GoogleAdsException", "KeywordMetricsGuardError", "ValueError", "RuntimeError"} or any(
        token in message for token in ("oauth", "developer token", "permission", "unauthorized", "unsupported api", "transport", "grpc", "malformed")
    )


def _provider_reached(exc: BaseException) -> bool:
    """Conservatively distinguish provider responses from pre-provider failures."""
    name = type(exc).__name__.casefold()
    message = str(exc).casefold()
    if any(token in message for token in ("credential_refresh", "dns", "tls", "connection", "timeout", "transport")):
        return False
    return name in {"googleadsexception", "grpcerror"} or any(
        token in message for token in ("invalid_argument", "developer token", "permission", "unauthorized", "resource_exhausted", "grpc_status")
    )


def _safe_provider_error(exc: BaseException) -> str:
    """Keep telemetry useful without persisting exception payloads verbatim."""
    return f"{type(exc).__name__}: {str(exc)[:500]}"


@dataclass(frozen=True)
class StructuredLocation:
    city: str
    state_code: str
    country_code: str = "US"

    @property
    def identity(self) -> str:
        return f"{self.city.strip().casefold()}|{self.state_code.strip().casefold()}|{self.country_code.upper()}"


def estimate_provider_batches(keyword_count: int, target_count: int, chunk_size: int = 10_000, language_count: int = 1) -> int:
    """Pure preflight estimate; performs no cache lookup or provider work."""
    if keyword_count <= 0 or target_count <= 0 or language_count <= 0:
        return 0
    return ((keyword_count + chunk_size - 1) // chunk_size) * target_count * language_count


class MultiCityKeywordMetricsOrchestrator:
    def __init__(self, db: Session, provider, geo_resolver, *, fx_provider=None, customer_id=None, provider_currency_code=None, minimum_sv=260, freshness_days: int = 30, chunk_size: int = 10_000):
        self.db, self.provider, self.geo_resolver = db, provider, geo_resolver
        self.fx_provider, self.customer_id, self.provider_currency_code, self.minimum_sv = fx_provider, customer_id, provider_currency_code, minimum_sv
        self.freshness = timedelta(days=freshness_days)
        self.chunk_size = chunk_size

    def _mapping(self, location: StructuredLocation):
        now = datetime.utcnow()
        return self.db.query(ProviderGeoMapping).filter_by(city=location.city, state_code=location.state_code,
            country_code=location.country_code.upper(), provider=self.provider.provider_name).first()

    async def run(self, keywords: list[str], locations: list[StructuredLocation], *, batch: KeywordMetricBatch):
        previous_expire_on_commit = self.db.expire_on_commit
        # Long-running orchestration keeps a bounded in-memory ledger of ORM
        # items across checkpoint commits. Expiring those instances forces a
        # SELECT before each subsequent status update.
        self.db.expire_on_commit = False
        keywords = list(dict.fromkeys(k.strip() for k in keywords if k and k.strip()))
        locations = list({x.identity: x for x in locations}.values())
        report = {"geo_cache_hits": 0, "geo_live_requests": 0, "geo_successes": 0, "geo_not_found": 0, "geo_ambiguous": 0, "geo_failures": 0, "geo_blocked_by_circuit": 0,
                  "historical_cache_hits": 0, "historical_live_requests": 0, "historical_successes": 0,
                  "historical_failures": 0, "fx_cache_hits": 0, "fx_live_requests": 0, "fx_failures": 0, "automatic_retries": 0, "other_provider_requests": 0,
                  "results": [], "failed_items": [], "planned_rpc_count": 0,
                  "actual_rpc_count": 0, "keywords_per_rpc": [], "cache_saved_keyword_items": 0,
                  "locations_count": len(locations), "languages_count": 1}
        currency_resolution = resolve_cached_customer_currency(
            self.db, provider=self.provider.provider_name, customer_id=self.customer_id,
            override=self.provider_currency_code,
        )
        currency = currency_resolution.currency_code
        report.update({
            "currency_source": currency_resolution.source,
            "currency_metadata_cache_hit": currency_resolution.cache_hit,
            "google_customer_currency_resolved": bool(currency),
            "customer_id": self.customer_id,
            "fx_required": bool(currency and currency.upper() != "USD"),
        })
        fx_rate = None
        circuit_signature = None
        systemic_seen = 0
        mappings = {}
        attempted_geo_failures = set()
        geo_diagnostics = {}
        for location in locations:
            cached = self._mapping(location)
            if cached and cached.fresh_until and cached.fresh_until > datetime.utcnow() and cached.mapping_status == "MAPPED":
                mappings[location.identity] = cached; report["geo_cache_hits"] += 1; continue
            try:
                report["geo_live_requests"] += 1
                resolved = await self.geo_resolver.resolve(location.city, location.state_code, location.country_code)
                mapping = cached or ProviderGeoMapping(city=location.city, state_code=location.state_code, country_code=location.country_code.upper(), provider=self.provider.provider_name)
                mapping.criterion_id, mapping.resource_name = resolved.criterion_id, resolved.resource_name
                mapping.provider_name, mapping.target_type, mapping.provider_status = resolved.provider_name, resolved.target_type, resolved.status
                mapping.mapping_status, mapping.fetched_at, mapping.fresh_until = "MAPPED", datetime.utcnow(), datetime.utcnow() + self.freshness
                mapping.provenance = {"source": "google_ads_geo", "mapping_status": resolved.mapping_status}
                self.db.add(mapping); self.db.flush(); mappings[location.identity] = mapping
                report["geo_successes"] += 1
            except Exception as exc:
                report["geo_failures"] += 1
                attempted_geo_failures.add(location.identity)
                geo_diagnostics[location.identity] = {"failure": str(exc)[:120], **getattr(exc, "diagnostic", {})}
                if "NOT_FOUND" in str(exc): report["geo_not_found"] += 1
                if "AMBIGUOUS" in str(exc): report["geo_ambiguous"] += 1
                if is_systemic_failure(self.provider.provider_name, "geo", exc):
                    signature = failure_signature(self.provider.provider_name, "geo", exc)
                    systemic_seen = systemic_seen + 1 if signature == circuit_signature else 1
                    circuit_signature = signature
                    if systemic_seen >= 2:
                        report["circuit_open"] = True
                        break
                report["failed_items"].append({"location": location.identity, "status": "GEO_FAILED", "error": type(exc).__name__, "diagnostic": getattr(exc, "diagnostic", {})})
        work = []
        existing_items = {
            (row.keyword, row.location_identity): row
            for row in self.db.query(KeywordMetricBatchItem).filter_by(batch_id=batch.id).all()
        }
        new_items = []
        for keyword in keywords:
            for location in locations:
                mapping = mappings.get(location.identity)
                item = existing_items.get((keyword, location.identity))
                if item is None:
                    item = KeywordMetricBatchItem(batch_id=batch.id, keyword=keyword, city=location.city, state_code=location.state_code,
                        country_code=location.country_code, location_identity=location.identity, status="PENDING", geo_mapping_id=mapping.id if mapping else None)
                    existing_items[(keyword, location.identity)] = item
                    new_items.append(item)
                elif mapping and item.geo_mapping_id != mapping.id:
                    item.geo_mapping_id = mapping.id
                if not mapping:
                    item.status = "BLOCKED_BY_SYSTEMIC_FAILURE" if circuit_signature and report.get("circuit_open") and location.identity not in attempted_geo_failures else "GEO_FAILED"
                    item.error_code = "BLOCKED_BY_SYSTEMIC_FAILURE" if item.status == "BLOCKED_BY_SYSTEMIC_FAILURE" else "GEO_FAILED"
                    item.geo_diagnostic = geo_diagnostics.get(location.identity, {})
                    if item.status == "BLOCKED_BY_SYSTEMIC_FAILURE": report["geo_blocked_by_circuit"] += 1
                    continue
                target = {"geo_target_ids": [mapping.criterion_id]}
                request = KeywordMetricRequest(keyword=keyword, location_name=f"{location.city}, {location.state_code}", language_code="en", country_code=location.country_code, location_target=target)
                work.append((item, request))
        for start in range(0, len(new_items), 1000):
            self.db.add_all(new_items[start:start + 1000])
            self.db.flush()
        report["batch_items_loaded"] = len(existing_items) - len(new_items)
        report["batch_items_inserted"] = len(new_items)
        # Snapshot scalar item fields before the checkpoint commit.  The
        # default SQLAlchemy session expires ORM instances on commit; reading
        # item.id/city/keyword later in the report loop would otherwise issue
        # one refresh (and implicit autoflush) per result.
        item_details = {id(item): (item.id, item.city, item.keyword) for item, _ in work}
        self.db.commit()
        # Resolve fresh evidence before transport, then group unresolved
        # keywords by identical target semantics. One provider call may serve
        # many keywords for one city; cities are never merged together.
        pending_by_target = {}
        fresh_evidence = {}
        # One evidence query per target replaces the previous per-item cache
        # query. The complete identity remains enforced by provider, target,
        # language, country, and normalized keyword.
        for target, entries in {}.fromkeys(request.location_name for _, request in work).items():
            target_entries = [(item, request) for item, request in work if request.location_name == target]
            if not target_entries:
                continue
            first_request = target_entries[0][1]
            rows = self.db.query(KeywordMetricEvidence).filter(
                KeywordMetricEvidence.provider == self.provider.provider_name,
                KeywordMetricEvidence.location_name == target,
                KeywordMetricEvidence.language_code == first_request.language_code,
                KeywordMetricEvidence.country_code == first_request.country_code,
                KeywordMetricEvidence.submitted_keyword.in_([request.keyword for _, request in target_entries]),
            ).order_by(KeywordMetricEvidence.fetched_at.desc()).all()
            for row in rows:
                key = (target, row.submitted_keyword.casefold())
                if key not in fresh_evidence and row.fresh_until and row.fresh_until > datetime.utcnow():
                    fresh_evidence[key] = row
        processed_items = 0
        def checkpoint_item():
            nonlocal processed_items
            processed_items += 1
            if processed_items % 1000 == 0:
                self.db.commit()
        for item, request in work:
            existing = fresh_evidence.get((request.location_name, request.keyword.casefold()))
            if existing and existing.fresh_until and existing.fresh_until > datetime.utcnow():
                report["cache_saved_keyword_items"] += 1
            else:
                pending_by_target.setdefault(request.location_name, []).append((item, request))
        report["planned_rpc_count"] = sum((len(entries) + self.chunk_size - 1) // self.chunk_size for entries in pending_by_target.values())
        if report["cache_saved_keyword_items"]:
            provider_name = getattr(self.provider, "provider_name", "unknown")
            reuse_call = safe_create_provider_call(self.db, lambda: ProviderCall(
                provider=provider_name,
                execution_mode="LIVE" if getattr(self.provider, "is_live_transport", False) else "MOCK",
                stage="keyword_metrics", operation="CACHE_REUSE", request_cache_key="keyword-metrics-reuse:" + hashlib.sha256(
                    f"{batch.id}|{report['cache_saved_keyword_items']}".encode("utf-8")
                ).hexdigest(),
                outcome="CACHE_HIT", cache_hit=True, source_kind="cache", started_at=datetime.utcnow(),
                actual_cost=None, estimated_cost=None, currency=None,
                logical_item_count=len(work), unique_target_count=len(fresh_evidence),
                cache_hit_count=report["cache_saved_keyword_items"], cache_miss_count=sum(len(v) for v in pending_by_target.values()),
                stale_count=0, cache_outcome="HIT", cache_provider_dimension=provider_name,
                actual_evidence_provider=provider_name,
                evidence_reused_count=report["cache_saved_keyword_items"], evidence_created_count=0,
                evidence_partial_count=0, evidence_missing_count=0,
                provider_item_count=0, batch_size=0, batch_count=0, http_request_count=0,
                http_request_sent=False, paid_attempt=False, retry_count=0, cost_confidence="NOT_APPLICABLE",
            ))
        batched_results = {}
        chunk_telemetry = []
        for target, entries in pending_by_target.items():
            for start in range(0, len(entries), self.chunk_size):
                chunk = entries[start:start + self.chunk_size]
                chunk_index = (start // self.chunk_size) + 1
                first_request = chunk[0][1]
                location_target = first_request.location_target or {}
                geo_targets = location_target.get("geo_target_constants") or location_target.get("geo_targets") or []
                geo_resource = geo_targets[0] if geo_targets else None
                cache_key = "keyword-metrics:" + hashlib.sha256(
                    f"{batch.id}|{target}|{chunk_index}".encode("utf-8")
                ).hexdigest()
                provider_name = getattr(self.provider, "provider_name", "unknown")
                live_transport = bool(getattr(self.provider, "is_live_transport", False))
                provider_call = safe_create_provider_call(self.db, lambda: ProviderCall(
                    provider=provider_name,
                    execution_mode="LIVE" if live_transport else "MOCK",
                    stage="keyword_metrics",
                    operation="generate_keyword_historical_metrics",
                    request_cache_key=cache_key,
                    outcome="STARTED",
                    cache_hit=False,
                    source_kind="live_api" if live_transport else "mock",
                    units=None,
                    started_at=datetime.utcnow(),
                    estimated_cost=None,
                    actual_cost=None,
                    currency=None,
                    customer_id=self.customer_id,
                    target_identity=target,
                    geo_target_resource=geo_resource,
                    language_code=first_request.language_code,
                    chunk_index=chunk_index,
                    chunk_count=report["planned_rpc_count"],
                    submitted_keyword_count=len(chunk),
                    attempt_number=1,
                    provider_reached=None,
                    operation_count=None,
                    logical_item_count=len(chunk),
                    unique_target_count=len({request.keyword.casefold() for _, request in chunk}),
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
                chunk_telemetry.append((provider_call, [id(item) for item, _ in chunk]))
                # Persist STARTED before transport so an interrupted process is
                # auditable as an incomplete attempt rather than disappearing.
                try:
                    returned = await self.provider.fetch([request for _, request in chunk])
                    finished_at = datetime.utcnow()
                    if provider_call is not None:
                        safe_update_provider_call(self.db, provider_call,
                            finished_at=finished_at,
                            duration_ms=max(0.0, (finished_at - provider_call.started_at).total_seconds() * 1000),
                            outcome="SUCCESS", provider_reached=live_transport,
                            operation_count=1 if live_transport else 0, actual_cost=None,
                            items_returned_count=sum(1 for item in returned if item is not None and not (isinstance(item.raw, dict) and item.raw.get("mapping_status") == "NOT_FOUND")),
                            items_failed_count=max(0, len(chunk) - sum(1 for item in returned if item is not None and not (isinstance(item.raw, dict) and item.raw.get("mapping_status") == "NOT_FOUND"))))
                    report["historical_live_requests"] += 1
                    report["actual_rpc_count"] += 1
                    report["keywords_per_rpc"].append(len(chunk))
                    for result in returned:
                        batched_results[(target, result.keyword)] = result
                        if result.provider_keyword:
                            batched_results[(target, result.provider_keyword)] = result
                except Exception as exc:
                    finished_at = datetime.utcnow()
                    reached = _provider_reached(exc)
                    if provider_call is not None:
                        outcome = "BUDGET_EXCEEDED" if isinstance(exc, OperationBudgetExceeded) else ("PROVIDER_REJECTED" if reached else "NETWORK_FAILURE_BEFORE_PROVIDER")
                        safe_update_provider_call(self.db, provider_call,
                            finished_at=finished_at,
                            duration_ms=max(0.0, (finished_at - provider_call.started_at).total_seconds() * 1000),
                            provider_reached=reached, operation_count=1 if reached else 0,
                            actual_cost=None, items_returned_count=0,
                            items_failed_count=len(chunk), outcome=outcome,
                            error_category=type(exc).__name__, error_message=_safe_provider_error(exc))
                    report["historical_live_requests"] += 1
                    report["historical_failures"] += len(chunk)
                    for item, _ in chunk:
                        item.status, item.error_code, item.error_message = "PROVIDER_FAILED", type(exc).__name__, str(exc)[:500]
                    self.db.commit()
        # Resolve one applicable FX rate for the whole run before entering the
        # result loop.  The customer currency/request context is shared by all
        # results; resolving persisted FX per result causes repeated ORM
        # queries and autoflushes at scale.
        if currency and currency.upper() != "USD":
            try:
                if self.fx_provider:
                    fx_rate = await self.fx_provider.get_rate(currency, "USD")
                    calls = getattr(self.fx_provider, "network_calls", 0)
                    report["fx_live_requests"] = min(calls, 1)
                    report["fx_cache_hits"] = int(calls == 0)
                else:
                    fx_rate = resolve_persisted_fx(self.db, currency, "USD")
                    report["fx_cache_hits"] = int(fx_rate is not None)
            except Exception:
                report["fx_failures"] += 1
        for item, request in work:
            existing = fresh_evidence.get((request.location_name, request.keyword.casefold()))
            if existing and existing.fresh_until and existing.fresh_until > datetime.utcnow():
                item_id, city, submitted_keyword = item_details[id(item)]
                item.status, item.evidence_id = "CACHE_HIT", existing.id; report["historical_cache_hits"] += 1; report["results"].append({"item_id": item_id, "evidence_id": existing.id, "city": city, "keyword": submitted_keyword, "status": "CACHE_HIT"}); checkpoint_item(); continue
            try:
                result = batched_results.get((request.location_name, request.keyword))
                if not result:
                    item.status = "UNMAPPED"; report["historical_failures"] += 1; checkpoint_item(); continue
                query = KeywordMetricQuery(id=uid(), submitted_keyword=request.keyword, normalized_keyword=request.keyword.casefold(), location_name=request.location_name, location_target=request.location_target or {}, language_code="en", country_code=request.country_code, provider=result.provider, status="MAPPED")
                self.db.add(query)
                result.provider_currency_code = result.provider_currency_code or currency
                usd = resolve_usd_metrics(self.db, provider_currency=result.provider_currency_code, cpc=result.cpc, low_bid=result.low_bid, high_bid=result.high_bid, customer_id=self.customer_id, fx_rate=fx_rate)
                result.usd_cpc, result.usd_low_bid, result.usd_high_bid = usd.usd_cpc, usd.usd_low_bid, usd.usd_high_bid
                result.fx_rate, result.fx_rate_date, result.fx_source = usd.fx_rate, usd.fx_rate_date, usd.fx_source
                evidence = KeywordMetricEvidence(id=uid(), query_id=query.id, submitted_keyword=request.keyword, provider_keyword=result.provider_keyword or result.keyword, normalized_keyword=request.keyword.casefold(), location_name=request.location_name, location_target=request.location_target or {}, language_code="en", country_code=request.country_code, provider=result.provider, source_kind=result.provider, avg_monthly_searches=result.avg_monthly_searches, competition=result.competition, competition_index=result.competition_index, cpc=result.cpc, low_bid=result.low_bid, high_bid=result.high_bid, provider_currency_code=result.provider_currency_code, usd_cpc=result.usd_cpc, usd_low_bid=result.usd_low_bid, usd_high_bid=result.usd_high_bid, fx_rate=result.fx_rate, fx_rate_date=result.fx_rate_date, fx_source=result.fx_source, monthly_history=result.monthly_history, raw_payload=result.raw or {}, fetched_at=datetime.utcnow(), fresh_until=datetime.utcnow() + self.freshness, cost=result.cost, mapping_status="MAPPED")
                self.db.add(evidence); item.status, item.evidence_id = "MAPPED", evidence.id; item.policy_minimum_sv = self.minimum_sv; item.policy_status = "MISSING_EVIDENCE" if result.avg_monthly_searches is None else ("ELIGIBLE_FOR_RANK_RENT_PIPELINE" if result.avg_monthly_searches >= self.minimum_sv else "BELOW_SV_THRESHOLD"); item.policy_snapshot = {"minimum_sv": self.minimum_sv}; item.evaluated_at = datetime.utcnow(); report["historical_successes"] += 1
                item_id, city, submitted_keyword = item_details[id(item)]
                report["results"].append({"item_id": item_id, "evidence_id": evidence.id, "city": city, "keyword": submitted_keyword, "status": "MAPPED", "search_volume": result.avg_monthly_searches, "trend_status": "COMPLETE_12M" if len(result.monthly_history or []) == 12 else ("PARTIAL" if result.monthly_history else "MISSING")})
                checkpoint_item()
            except Exception as exc:
                item.status, item.error_code, item.error_message = "PROVIDER_FAILED", type(exc).__name__, str(exc)[:500]; report["historical_failures"] += 1; checkpoint_item()
        # The normal evidence transaction remains authoritative. Once all
        # evidence objects have been flushed, finalize only observational counts
        # on their originating chunk rows. A telemetry update cannot roll back
        # the business work because it is savepoint-isolated.
        self.db.flush()
        item_by_id = {id(item): item for item, _ in work}
        for provider_call, item_ids in chunk_telemetry:
            if provider_call is None:
                continue
            created = sum(1 for item_id in item_ids if item_by_id[item_id].status == "MAPPED")
            try:
                safe_update_provider_call(
                    self.db, provider_call,
                    evidence_created_count=created,
                evidence_missing_count=len(item_ids) - created,
                actual_cost=None, estimated_cost=None,
                )
            except Exception as exc:  # defensive boundary around observational finalization
                import logging
                logging.getLogger(__name__).warning("provider_call_telemetry_finalization_failed: %s", type(exc).__name__)
        batch.status = "COMPLETED"; batch.deduplicated_count = len(work); batch.returned_count = report["historical_successes"] + report["historical_cache_hits"]; batch.mapped_count = batch.returned_count; batch.unmapped_count = len(report["failed_items"]) + report["historical_failures"]; self.db.commit()
        self.db.expire_on_commit = previous_expire_on_commit
        return report
