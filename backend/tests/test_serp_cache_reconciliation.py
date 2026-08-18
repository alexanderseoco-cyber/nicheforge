from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.entities import ProviderCache, SerpResultRow, SerpSnapshot
from app.services.provider_cache import upsert_provider_cache


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _snapshot(db, *, raw=None):
    snapshot = SerpSnapshot(
        candidate_id="pipeline", candidate_entity_id="entity-1", provider="dataforseo_trial",
        keyword="tree service albany", location_name="Albany, NY", raw_payload=raw or {},
        fetched_at=datetime.utcnow(), fresh_until=datetime.utcnow() + timedelta(days=7),
        requested_depth=10, source_kind="dataforseo_trial",
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def test_invalid_cache_pointer_is_reused_for_new_valid_snapshot(db_session):
    key = "serp-cache-key"
    old = _snapshot(db_session, raw={"response": {"status_code": 40501}})
    old_cache = upsert_provider_cache(db_session, cache_key=key, provider=old.provider, operation="serp", evidence_type="serp", evidence_id=old.id, fetched_at=old.fetched_at, fresh_until=old.fresh_until, status="invalid")
    new = _snapshot(db_session, raw={"response": {"status_code": 20000}})
    current = upsert_provider_cache(db_session, cache_key=key, provider=new.provider, operation="serp", evidence_type="serp", evidence_id=new.id, fetched_at=new.fetched_at, fresh_until=new.fresh_until)
    assert current.id == old_cache.id
    assert current.evidence_id == new.id
    assert db_session.get(SerpSnapshot, old.id).raw_payload["response"]["status_code"] == 40501


def test_stale_valid_cache_pointer_is_replaced_without_deleting_evidence(db_session):
    key = "serp-cache-key"
    old = _snapshot(db_session, raw={"response": {"status_code": 20000}})
    cache = upsert_provider_cache(db_session, cache_key=key, provider=old.provider, operation="serp", evidence_type="serp", evidence_id=old.id, fetched_at=old.fetched_at, fresh_until=datetime.utcnow() - timedelta(days=1))
    new = _snapshot(db_session, raw={"response": {"status_code": 20000}})
    current = upsert_provider_cache(db_session, cache_key=key, provider=new.provider, operation="serp", evidence_type="serp", evidence_id=new.id, fetched_at=new.fetched_at, fresh_until=new.fresh_until)
    assert current.id == cache.id
    assert db_session.get(SerpSnapshot, old.id) is not None


def test_fresh_cache_pointer_is_reused_without_new_pointer(db_session):
    key = "serp-cache-key"
    snapshot = _snapshot(db_session, raw={"response": {"status_code": 20000}})
    first = upsert_provider_cache(db_session, cache_key=key, provider=snapshot.provider, operation="serp", evidence_type="serp", evidence_id=snapshot.id, fetched_at=snapshot.fetched_at, fresh_until=snapshot.fresh_until)
    second = upsert_provider_cache(db_session, cache_key=key, provider=snapshot.provider, operation="serp", evidence_type="serp", evidence_id=snapshot.id, fetched_at=snapshot.fetched_at, fresh_until=snapshot.fresh_until)
    assert second.id == first.id
    assert db_session.query(ProviderCache).filter_by(cache_key=key).count() == 1
