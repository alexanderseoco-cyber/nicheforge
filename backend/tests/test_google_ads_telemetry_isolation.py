import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.entities import KeywordMetricBatch, KeywordMetricEvidence
from app.models.entities import ProviderCall
from app.providers.contracts import KeywordMetricRequest, KeywordMetricResult
from app.services.keyword_metrics_batch import KeywordMetricsBatchOrchestrator
from app.services.keyword_metrics_multi_city import MultiCityKeywordMetricsOrchestrator, StructuredLocation


class Provider:
    provider_name = "google_ads"
    is_live_transport = False

    def __init__(self):
        self.calls = 0

    async def fetch(self, requests):
        self.calls += 1
        return [KeywordMetricResult(
            r.keyword, 321, cpc=12.34, competition=0.27, competition_index=73,
            low_bid=4.56, high_bid=78.90, provider="google_ads",
            provider_keyword=r.keyword, provider_currency_code="USD", cost=0.0,
        ) for r in requests]


class Resolver:
    async def resolve(self, city, state, country):
        return type("Geo", (), {"criterion_id": "100", "resource_name": "geoTargetConstants/100", "provider_name": "google_ads", "target_type": "CITY", "status": "ENABLED", "mapping_status": "MAPPED"})()


def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


@pytest.mark.asyncio
async def test_batch_provider_result_survives_provider_call_construction_failure(monkeypatch):
    db = session()
    provider = Provider()
    monkeypatch.setattr("app.services.keyword_metrics_batch.ProviderCall", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("construction failure")))
    request = KeywordMetricRequest("tree removal", "Albany, GA", "en", "US", {})

    result = await KeywordMetricsBatchOrchestrator(provider, db=db).execute([request])

    assert provider.calls == 1
    assert result.provider_requests == 1
    metric = result.results["tree removal"]
    assert (metric.avg_monthly_searches, metric.cpc, metric.competition) == (321, 12.34, 0.27)
    assert (metric.competition_index, metric.low_bid, metric.high_bid) == (73, 4.56, 78.90)
    assert metric.provider_currency_code == "USD"
    assert metric.provider == "google_ads"
    assert db.query(KeywordMetricBatch).count() == 0
    db.add(KeywordMetricBatch(provider="google_ads", submitted_count=1, status="CHECK"))
    db.flush()
    assert db.query(KeywordMetricBatch).count() == 1


@pytest.mark.asyncio
async def test_multi_city_continues_and_persists_evidence_when_telemetry_construction_fails(monkeypatch):
    db = session()
    provider = Provider()
    batch = KeywordMetricBatch(provider="google_ads", submitted_count=2, status="RUNNING")
    db.add(batch)
    db.flush()
    monkeypatch.setattr("app.services.keyword_metrics_multi_city.ProviderCall", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("construction failure")))

    report = await MultiCityKeywordMetricsOrchestrator(db, provider, Resolver()).run(
        ["tree removal"], [StructuredLocation("Albany", "GA"), StructuredLocation("Dothan", "AL")], batch=batch
    )

    assert provider.calls == 2
    assert report["historical_live_requests"] == 2
    assert report["historical_successes"] == 2
    assert db.query(KeywordMetricEvidence).count() == 2
    evidence = db.query(KeywordMetricEvidence).first()
    assert (evidence.avg_monthly_searches, evidence.cpc, evidence.competition) == (321, 12.34, 0.27)
    assert (evidence.competition_index, evidence.low_bid, evidence.high_bid) == (73, 4.56, 78.90)
    assert evidence.provider_currency_code == "USD"
    assert evidence.provider == "google_ads"
    db.query(KeywordMetricBatch).count()


@pytest.mark.asyncio
async def test_batch_provider_call_records_chunk_measurement_without_api_cost_claim():
    db = session()
    provider = Provider()
    requests = [KeywordMetricRequest(f"keyword {i}", "Albany, GA", "en", "US", {}) for i in range(3)]

    result = await KeywordMetricsBatchOrchestrator(provider, chunk_size=2, db=db).execute(requests)

    calls = db.query(ProviderCall).order_by(ProviderCall.chunk_index).all()
    assert result.provider_requests == provider.calls == 2
    assert [call.provider_item_count for call in calls] == [2, 1]
    assert [call.logical_item_count for call in calls] == [2, 1]
    assert [call.cache_miss_count for call in calls] == [2, 1]
    assert all(call.cache_hit_count == 0 and call.stale_count == 0 for call in calls)
    assert all(call.batch_size == call.provider_item_count and call.batch_count == 1 for call in calls)
    assert all(call.http_request_count == 0 and call.http_request_sent is False for call in calls)
    assert all(call.retry_count == 0 and call.actual_cost is None and call.cost_confidence == "UNKNOWN" for call in calls)
    assert all(call.items_returned_count == call.provider_item_count and call.items_failed_count == 0 for call in calls)


@pytest.mark.asyncio
async def test_full_cache_reuse_is_not_counted_as_google_ads_acquisition():
    db = session()
    provider = Provider()
    request = KeywordMetricRequest("tree removal", "Albany, GA", "en", "US", {})
    key = KeywordMetricsBatchOrchestrator._key(request)
    cached = type("Cached", (), {"result": KeywordMetricResult("tree removal", 999, provider="google_ads"), "fresh": True})()

    result = await KeywordMetricsBatchOrchestrator(provider, cache={key: cached}, db=db).execute([request])

    reuse = db.query(ProviderCall).one()
    assert provider.calls == result.provider_requests == 0
    assert reuse.operation == "CACHE_REUSE"
    assert (reuse.provider_item_count, reuse.http_request_count, reuse.http_request_sent, reuse.paid_attempt) == (0, 0, False, False)
    assert (reuse.evidence_reused_count, reuse.evidence_created_count, reuse.evidence_missing_count) == (1, 0, 0)
    assert reuse.actual_evidence_provider == "google_ads"


@pytest.mark.asyncio
async def test_duplicate_logical_requests_are_deduplicated_before_provider_chunking():
    db = session()
    provider = Provider()
    request = KeywordMetricRequest("Tree Removal", "Albany, GA", "en", "US", {})
    duplicate = KeywordMetricRequest("tree removal", "Albany, GA", "en", "US", {})

    result = await KeywordMetricsBatchOrchestrator(provider, db=db).execute([request, duplicate])

    acquisition = db.query(ProviderCall).filter(ProviderCall.operation != "CACHE_REUSE").one()
    assert result.submitted_count == 2 and result.deduplicated_count == 1
    assert provider.calls == 1
    assert acquisition.logical_item_count == acquisition.unique_target_count == acquisition.provider_item_count == 1


@pytest.mark.asyncio
async def test_partial_provider_return_reconciles_submitted_and_failed_items():
    db = session()
    provider = Provider()
    original_fetch = provider.fetch

    async def partial_fetch(requests):
        returned = await original_fetch(requests[:1])
        return returned

    provider.fetch = partial_fetch
    requests = [KeywordMetricRequest(f"keyword {i}", "Albany, GA", "en", "US", {}) for i in range(2)]
    await KeywordMetricsBatchOrchestrator(provider, db=db).execute(requests)
    acquisition = db.query(ProviderCall).filter(ProviderCall.operation != "CACHE_REUSE").one()
    assert (acquisition.provider_item_count, acquisition.items_returned_count, acquisition.items_failed_count) == (2, 1, 1)


@pytest.mark.asyncio
async def test_multi_city_finalizes_created_and_missing_evidence_per_chunk():
    db = session()
    provider = Provider()
    batch = KeywordMetricBatch(provider="google_ads", submitted_count=2, status="RUNNING")
    db.add(batch)
    db.flush()

    await MultiCityKeywordMetricsOrchestrator(db, provider, Resolver(), chunk_size=2).run(
        ["tree removal", "roof repair"], [StructuredLocation("Albany", "GA")], batch=batch
    )

    acquisition = db.query(ProviderCall).filter(ProviderCall.operation == "generate_keyword_historical_metrics").one()
    assert (acquisition.evidence_created_count, acquisition.evidence_missing_count) == (2, 0)
    assert db.query(KeywordMetricEvidence).count() == 2


@pytest.mark.asyncio
async def test_post_persistence_finalization_failure_cannot_rollback_evidence(monkeypatch):
    db = session()
    provider = Provider()
    batch = KeywordMetricBatch(provider="google_ads", submitted_count=1, status="RUNNING")
    db.add(batch)
    db.flush()
    from app.services import keyword_metrics_multi_city as module
    from app.services.provider_call_telemetry import safe_update_provider_call as real_update
    calls = 0

    def fail_finalization(db_session, provider_call, **values):
        nonlocal calls
        calls += 1
        if "evidence_created_count" in values:
            raise RuntimeError("injected finalization failure")
        return real_update(db_session, provider_call, **values)

    monkeypatch.setattr(module, "safe_update_provider_call", fail_finalization)
    report = await MultiCityKeywordMetricsOrchestrator(db, provider, Resolver()).run(
        ["tree removal"], [StructuredLocation("Albany", "GA")], batch=batch
    )

    evidence = db.query(KeywordMetricEvidence).one()
    assert provider.calls == 1 and report["historical_successes"] == 1 and calls >= 2
    assert (evidence.avg_monthly_searches, evidence.cpc, evidence.competition) == (321, 12.34, 0.27)
    assert (evidence.competition_index, evidence.low_bid, evidence.high_bid) == (73, 4.56, 78.90)
    assert evidence.provider_currency_code == "USD" and evidence.provider == "google_ads"
    db.add(KeywordMetricBatch(provider="google_ads", submitted_count=0, status="SESSION_HEALTH"))
    db.flush()
    acquisition = db.query(ProviderCall).filter(ProviderCall.operation == "generate_keyword_historical_metrics").one()
    assert acquisition.evidence_created_count is None and acquisition.evidence_missing_count is None


def test_google_ads_cost_and_operation_category_aggregation_is_query_safe():
    db = session()
    db.add_all([
        ProviderCall(provider="google_ads", stage="keyword_metrics", operation="generate_keyword_historical_metrics", request_cache_key="a", outcome="SUCCESS", source_kind="mock", logical_item_count=4, unique_target_count=4, provider_item_count=4, batch_count=1, http_request_count=1, items_returned_count=4, items_failed_count=0, evidence_created_count=4, evidence_missing_count=0, actual_cost=None, estimated_cost=None, currency=None, cost_confidence="UNKNOWN"),
        ProviderCall(provider="google_ads", stage="keyword_metrics", operation="generate_keyword_historical_metrics", request_cache_key="b", outcome="SUCCESS", source_kind="mock", logical_item_count=4, unique_target_count=4, provider_item_count=4, batch_count=1, http_request_count=1, items_returned_count=3, items_failed_count=1, evidence_created_count=3, evidence_missing_count=1, actual_cost=None, estimated_cost=None, currency=None, cost_confidence="UNKNOWN"),
        ProviderCall(provider="google_ads", stage="keyword_metrics", operation="CACHE_REUSE", request_cache_key="r", outcome="CACHE_HIT", source_kind="cache", logical_item_count=3, unique_target_count=3, provider_item_count=0, batch_count=0, http_request_count=0, evidence_reused_count=3, evidence_created_count=0, evidence_missing_count=0, actual_cost=None, estimated_cost=None, currency=None, cost_confidence="NOT_APPLICABLE"),
    ])
    db.flush()
    acquisition = db.query(ProviderCall).filter(ProviderCall.operation == "generate_keyword_historical_metrics").all()
    reuse = db.query(ProviderCall).filter(ProviderCall.operation == "CACHE_REUSE").all()
    assert sum(row.logical_item_count for row in acquisition) + sum(row.logical_item_count for row in reuse) == 11
    assert sum(row.provider_item_count for row in acquisition) == 8
    assert sum(row.batch_count for row in acquisition) == 2
    assert sum(row.http_request_count for row in acquisition) == 2
    assert sum(row.items_returned_count for row in acquisition) == 7
    assert sum(row.items_failed_count for row in acquisition) == 1
    assert sum(row.evidence_reused_count or 0 for row in reuse) == 3
    assert sum(row.evidence_created_count for row in acquisition) == 7
    assert sum(row.evidence_missing_count for row in acquisition) == 1
    assert all(row.actual_cost is None and row.estimated_cost is None for row in acquisition + reuse)
