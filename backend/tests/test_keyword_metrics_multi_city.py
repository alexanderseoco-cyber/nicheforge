from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.entities import KeywordMetricBatch, ProviderGeoMapping
from app.models.entities import ProviderCustomerMetadata
from app.providers.contracts import KeywordMetricResult
from app.services.keyword_metrics_multi_city import MultiCityKeywordMetricsOrchestrator, StructuredLocation


class FakeResolver:
    def __init__(self): self.calls = 0
    async def resolve(self, city, state, country):
        self.calls += 1
        return type("Geo", (), {"criterion_id": str(1000 + self.calls), "resource_name": f"geoTargetConstants/{1000 + self.calls}", "provider_name": "google_ads", "target_type": "CITY", "status": "ENABLED", "mapping_status": "MAPPED"})()


class FakeProvider:
    provider_name = "google_ads"
    def __init__(self): self.calls = 0
    async def fetch(self, requests):
        self.calls += 1
        return [KeywordMetricResult(r.keyword, 300 if "Albany" in (r.location_name or "") else 10, provider="google_ads", provider_keyword=r.keyword, cpc=100.0, low_bid=50.0, high_bid=200.0, monthly_history=[{"year": 2025, "month": 1, "searches": 0}], cost=0.0) for r in requests]


class FakeFx:
    network_calls = 0
    async def get_rate(self, source, target):
        from app.services.currency_normalization import FxRate
        return FxRate(source, target, 0.01, "2026-01-01", "mock_fx")


class SameTransportFailureResolver:
    def __init__(self): self.calls = 0
    async def resolve(self, city, state, country):
        self.calls += 1
        raise RuntimeError("TransportError: provider unavailable")


EXACT_FIFTY_CITIES = [
    ("Albany", "GA"), ("Dothan", "AL"), ("Decatur", "IL"), ("Kokomo", "IN"), ("Joplin", "MO"),
    ("Enid", "OK"), ("Lawton", "OK"), ("Owensboro", "KY"), ("Cape Girardeau", "MO"), ("Jonesboro", "AR"),
    ("Florence", "AL"), ("Gadsden", "AL"), ("Hot Springs", "AR"), ("Conway", "AR"), ("Pine Bluff", "AR"),
    ("Pueblo", "CO"), ("Grand Junction", "CO"), ("Norwich", "CT"), ("Dover", "DE"), ("Ocala", "FL"),
    ("Valdosta", "GA"), ("Warner Robins", "GA"), ("Idaho Falls", "ID"), ("Pocatello", "ID"), ("Terre Haute", "IN"),
    ("Muncie", "IN"), ("Dubuque", "IA"), ("Waterloo", "IA"), ("Salina", "KS"), ("Hutchinson", "KS"),
    ("Bowling Green", "KY"), ("Paducah", "KY"), ("Monroe", "LA"), ("Alexandria", "LA"), ("Bangor", "ME"),
    ("Hagerstown", "MD"), ("Battle Creek", "MI"), ("Bay City", "MI"), ("Mankato", "MN"), ("Rochester", "MN"),
    ("Meridian", "MS"), ("Hattiesburg", "MS"), ("Jefferson City", "MO"), ("Great Falls", "MT"), ("Billings", "MT"),
    ("Grand Island", "NE"), ("Kearney", "NE"), ("Carson City", "NV"), ("Farmington", "NM"), ("Roswell", "NM"),
]


@pytest.mark.asyncio
async def test_multi_city_persists_mappings_and_is_restart_safe():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session(); provider = FakeProvider(); resolver = FakeResolver()
    batch = KeywordMetricBatch(provider="google_ads", submitted_count=2, status="RUNNING"); db.add(batch); db.flush()
    locations = [StructuredLocation("Albany", "GA"), StructuredLocation("Dothan", "AL")]
    first = await MultiCityKeywordMetricsOrchestrator(db, provider, resolver).run(["tree removal service"], locations, batch=batch)
    assert first["geo_live_requests"] == 2 and first["historical_live_requests"] == 2
    second_batch = KeywordMetricBatch(provider="google_ads", submitted_count=2, status="RUNNING"); db.add(second_batch); db.flush()
    second = await MultiCityKeywordMetricsOrchestrator(db, provider, resolver).run(["tree removal service"], locations, batch=second_batch)
    assert second["geo_cache_hits"] == 2 and second["historical_cache_hits"] == 2
    assert resolver.calls == 2 and provider.calls == 2


@pytest.mark.asyncio
async def test_mocked_fifty_city_acceptance_and_same_batch_resume():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session(); provider = FakeProvider(); resolver = FakeResolver()
    batch = KeywordMetricBatch(provider="google_ads", submitted_count=50, status="RUNNING"); db.add(batch); db.flush()
    locations = [StructuredLocation(f"City {i}", "GA") for i in range(50)]
    first = await MultiCityKeywordMetricsOrchestrator(db, provider, resolver).run(["tree removal service"], locations, batch=batch)
    assert first["geo_live_requests"] == 50
    assert first["historical_live_requests"] == 50
    assert len(first["results"]) == 50
    second = await MultiCityKeywordMetricsOrchestrator(db, provider, resolver).run(["tree removal service"], locations, batch=batch)
    assert second["geo_cache_hits"] == 50 and second["historical_cache_hits"] == 50
    assert resolver.calls == 50 and provider.calls == 50


@pytest.mark.asyncio
async def test_batch_reuses_customer_currency_fx_and_persists_policy():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine); Session = sessionmaker(bind=engine); db = Session()
    db.add(ProviderCustomerMetadata(provider="google_ads", customer_id="4553815994", currency_code="PKR", time_zone="Asia/Karachi")); db.flush()
    provider = FakeProvider(); resolver = FakeResolver(); batch = KeywordMetricBatch(provider="google_ads", submitted_count=1, status="RUNNING"); db.add(batch); db.flush()
    result = await MultiCityKeywordMetricsOrchestrator(db, provider, resolver, fx_provider=FakeFx(), customer_id="4553815994", minimum_sv=260).run(["tree removal service"], [StructuredLocation("Albany", "GA")], batch=batch)
    from app.models.entities import KeywordMetricEvidence, KeywordMetricBatchItem
    evidence = db.query(KeywordMetricEvidence).one(); item = db.query(KeywordMetricBatchItem).one()
    assert evidence.provider_currency_code == "PKR" and evidence.usd_cpc == 1.0 and evidence.monthly_history[0]["searches"] == 0
    assert item.policy_status == "ELIGIBLE_FOR_RANK_RENT_PIPELINE" and result["fx_live_requests"] == 0


@pytest.mark.asyncio
async def test_exact_named_fifty_city_contract_has_fifty_distinct_work_items():
    assert len(EXACT_FIFTY_CITIES) == 50
    locations = [StructuredLocation(city, state) for city, state in EXACT_FIFTY_CITIES]
    assert len({location.identity for location in locations}) == 50
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine); Session = sessionmaker(bind=engine); db = Session()
    provider = FakeProvider(); resolver = FakeResolver(); batch = KeywordMetricBatch(provider="google_ads", submitted_count=50, status="RUNNING"); db.add(batch); db.flush()
    report = await MultiCityKeywordMetricsOrchestrator(db, provider, resolver).run(["tree removal service"], locations, batch=batch)
    from app.models.entities import KeywordMetricBatchItem
    items = db.query(KeywordMetricBatchItem).filter_by(batch_id=batch.id).all()
    assert len(items) == 50 and len(report["results"]) == 50
    assert all(item.keyword == "tree removal service" for item in items)
    assert all(item.status == "MAPPED" for item in items)


@pytest.mark.asyncio
async def test_systemic_geo_failure_opens_after_two_and_blocks_remaining():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine); Session = sessionmaker(bind=engine); db = Session()
    resolver = SameTransportFailureResolver(); batch = KeywordMetricBatch(provider="google_ads", submitted_count=50, status="RUNNING"); db.add(batch); db.flush()
    result = await MultiCityKeywordMetricsOrchestrator(db, FakeProvider(), resolver).run(["tree removal service"], [StructuredLocation(f"City {i}", "GA") for i in range(50)], batch=batch)
    from app.models.entities import KeywordMetricBatchItem
    items = db.query(KeywordMetricBatchItem).filter_by(batch_id=batch.id).all()
    assert resolver.calls == 2 and result["geo_live_requests"] == 2 and result["geo_failures"] == 2
    assert result["geo_blocked_by_circuit"] == 48
    assert sum(item.status == "BLOCKED_BY_SYSTEMIC_FAILURE" for item in items) == 48
    assert result.get("fx_live_requests", 0) == 0
