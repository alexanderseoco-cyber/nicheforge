"""Persistent, restart-safe orchestration for keyword x structured-city research."""
from __future__ import annotations

from datetime import datetime, timedelta
from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.models.entities import KeywordMetricBatch, KeywordMetricBatchItem, KeywordMetricEvidence, KeywordMetricQuery, ProviderGeoMapping, ProviderCustomerMetadata
from app.providers.contracts import KeywordMetricRequest
from app.services.keyword_metrics_batch import KeywordMetricsBatchOrchestrator
from app.services.currency_normalization import normalize_to_usd


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


@dataclass(frozen=True)
class StructuredLocation:
    city: str
    state_code: str
    country_code: str = "US"

    @property
    def identity(self) -> str:
        return f"{self.city.strip().casefold()}|{self.state_code.strip().casefold()}|{self.country_code.upper()}"


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
        keywords = list(dict.fromkeys(k.strip() for k in keywords if k and k.strip()))
        locations = list({x.identity: x for x in locations}.values())
        report = {"geo_cache_hits": 0, "geo_live_requests": 0, "geo_successes": 0, "geo_not_found": 0, "geo_ambiguous": 0, "geo_failures": 0, "geo_blocked_by_circuit": 0,
                  "historical_cache_hits": 0, "historical_live_requests": 0, "historical_successes": 0,
                  "historical_failures": 0, "fx_cache_hits": 0, "fx_live_requests": 0, "fx_failures": 0, "automatic_retries": 0, "other_provider_requests": 0,
                  "results": [], "failed_items": []}
        currency = self.provider_currency_code
        if not currency and self.customer_id:
            metadata = self.db.query(ProviderCustomerMetadata).filter_by(provider=self.provider.provider_name, customer_id=self.customer_id).first()
            currency = metadata.currency_code if metadata else None
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
        for keyword in keywords:
            for location in locations:
                mapping = mappings.get(location.identity)
                item = self.db.query(KeywordMetricBatchItem).filter_by(batch_id=batch.id, keyword=keyword, location_identity=location.identity).first()
                if item is None:
                    item = KeywordMetricBatchItem(batch_id=batch.id, keyword=keyword, city=location.city, state_code=location.state_code,
                        country_code=location.country_code, location_identity=location.identity, status="PENDING", geo_mapping_id=mapping.id if mapping else None)
                    self.db.add(item); self.db.flush()
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
        self.db.commit()
        for item, request in work:
            existing = self.db.query(KeywordMetricEvidence).filter_by(submitted_keyword=request.keyword, normalized_keyword=request.keyword.casefold(), provider=self.provider.provider_name, location_name=request.location_name, language_code="en", country_code=request.country_code).order_by(KeywordMetricEvidence.fetched_at.desc()).first()
            if existing and existing.fresh_until and existing.fresh_until > datetime.utcnow():
                item.status, item.evidence_id = "CACHE_HIT", existing.id; report["historical_cache_hits"] += 1; report["results"].append({"item_id": item.id, "evidence_id": existing.id, "city": item.city, "keyword": item.keyword, "status": item.status}); self.db.commit(); continue
            try:
                returned = await self.provider.fetch([request])
                report["historical_live_requests"] += 1
                result = returned[0] if returned else None
                if not result:
                    item.status = "UNMAPPED"; report["historical_failures"] += 1; self.db.commit(); continue
                query = KeywordMetricQuery(submitted_keyword=request.keyword, normalized_keyword=request.keyword.casefold(), location_name=request.location_name, location_target=request.location_target or {}, language_code="en", country_code=request.country_code, provider=result.provider, status="MAPPED")
                self.db.add(query); self.db.flush()
                result.provider_currency_code = result.provider_currency_code or currency
                if not fx_rate and result.provider_currency_code and result.provider_currency_code.upper() != "USD" and self.fx_provider:
                    try:
                        fx_rate = await self.fx_provider.get_rate(result.provider_currency_code, "USD")
                        calls = getattr(self.fx_provider, "network_calls", 0)
                        report["fx_live_requests"] = min(calls, 1); report["fx_cache_hits"] = int(calls == 0)
                    except Exception:
                        report["fx_failures"] += 1
                for source, target in ((result.cpc, "usd_cpc"), (result.low_bid, "usd_low_bid"), (result.high_bid, "usd_high_bid")):
                    value, rate = normalize_to_usd(source, result.provider_currency_code, rate=fx_rate)
                    setattr(result, target, value)
                    if rate: result.fx_rate, result.fx_rate_date, result.fx_source = rate.rate, rate.rate_date, rate.source
                evidence = KeywordMetricEvidence(query_id=query.id, submitted_keyword=request.keyword, provider_keyword=result.provider_keyword or result.keyword, normalized_keyword=request.keyword.casefold(), location_name=request.location_name, location_target=request.location_target or {}, language_code="en", country_code=request.country_code, provider=result.provider, source_kind=result.provider, avg_monthly_searches=result.avg_monthly_searches, competition=result.competition, competition_index=result.competition_index, cpc=result.cpc, low_bid=result.low_bid, high_bid=result.high_bid, provider_currency_code=result.provider_currency_code, usd_cpc=result.usd_cpc, usd_low_bid=result.usd_low_bid, usd_high_bid=result.usd_high_bid, fx_rate=result.fx_rate, fx_rate_date=result.fx_rate_date, fx_source=result.fx_source, monthly_history=result.monthly_history, raw_payload=result.raw or {}, fetched_at=datetime.utcnow(), fresh_until=datetime.utcnow() + self.freshness, cost=result.cost, mapping_status="MAPPED")
                self.db.add(evidence); self.db.flush(); item.status, item.evidence_id = "MAPPED", evidence.id; item.policy_minimum_sv = self.minimum_sv; item.policy_status = "MISSING_EVIDENCE" if result.avg_monthly_searches is None else ("ELIGIBLE_FOR_RANK_RENT_PIPELINE" if result.avg_monthly_searches >= self.minimum_sv else "BELOW_SV_THRESHOLD"); item.policy_snapshot = {"minimum_sv": self.minimum_sv}; item.evaluated_at = datetime.utcnow(); report["historical_successes"] += 1
                report["results"].append({"item_id": item.id, "evidence_id": evidence.id, "city": item.city, "keyword": item.keyword, "status": item.status, "search_volume": result.avg_monthly_searches, "trend_status": "COMPLETE_12M" if len(result.monthly_history or []) == 12 else ("PARTIAL" if result.monthly_history else "MISSING")})
                self.db.commit()
            except Exception as exc:
                item.status, item.error_code, item.error_message = "PROVIDER_FAILED", type(exc).__name__, str(exc)[:500]; report["historical_failures"] += 1; self.db.commit()
        batch.status = "COMPLETED"; batch.deduplicated_count = len(work); batch.returned_count = report["historical_successes"] + report["historical_cache_hits"]; batch.mapped_count = batch.returned_count; batch.unmapped_count = len(report["failed_items"]) + report["historical_failures"]; self.db.commit()
        return report
