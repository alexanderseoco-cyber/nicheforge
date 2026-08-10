from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.entities import (
    AuthorityEvidence,
    CandidateEntity,
    City,
    ImportBatch,
    ProviderCache,
    ProviderCall,
    SearchVolumeEvidence,
)
from app.services.cache_keys import evidence_is_fresh, provider_cache_key
from app.services.identity import canonical_identity, identity_key


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def make_entity(db):
    city = City(name="Salina", state_code="KS", population=47000, population_vintage="test")
    db.add(city)
    db.flush()
    canonical = canonical_identity("rodent control", "US-1600000")
    entity = CandidateEntity(
        canonical_identity=canonical,
        identity_key=identity_key(canonical),
        service_term_normalized="rodent control",
        city_id=city.id,
        canonical_keyword="rodent control salina ks",
    )
    db.add(entity)
    db.flush()
    return entity


def test_evidence_refresh_is_append_only_and_preserves_provenance():
    engine = make_db()
    with Session(engine) as db:
        entity = make_entity(db)
        first = SearchVolumeEvidence(
            candidate_entity_id=entity.id, keyword="rodent control salina ks",
            location_name="Salina, KS, United States", provider="mock", source_kind="mock",
            avg_monthly_searches=300, raw_payload={"version": 1},
            request_metadata={"location_id": "US-1600000"},
        )
        second = SearchVolumeEvidence(
            candidate_entity_id=entity.id, keyword=first.keyword,
            location_name=first.location_name, provider="mock", source_kind="mock",
            avg_monthly_searches=400, raw_payload={"version": 2},
            request_metadata=first.request_metadata,
        )
        db.add_all([first, second])
        db.commit()
        rows = db.query(SearchVolumeEvidence).order_by(SearchVolumeEvidence.fetched_at).all()
        assert len(rows) == 2
        assert rows[0].avg_monthly_searches == 300
        assert rows[0].raw_payload == {"version": 1}
        assert rows[1].avg_monthly_searches == 400


def test_cache_key_is_deterministic_and_separates_request_dimensions():
    base = dict(keyword="rodent control salina ks", location="Salina,KS", language="en", country="US")
    assert provider_cache_key("mock", "search_volume", **base) == provider_cache_key("MOCK", "SEARCH_VOLUME", **base)
    assert provider_cache_key("mock", "search_volume", **base) != provider_cache_key("mock", "search_volume", **{**base, "language": "es"})
    assert provider_cache_key("mock", "search_volume", **base) != provider_cache_key("dataforseo", "search_volume", **base)


def test_cache_pointer_is_typed_and_staleness_does_not_delete_evidence():
    engine = make_db()
    now = datetime.now(timezone.utc)
    with Session(engine) as db:
        entity = make_entity(db)
        evidence = SearchVolumeEvidence(
            candidate_entity_id=entity.id, keyword="rodent control salina ks", location_name="Salina, KS",
            provider="mock", source_kind="mock", avg_monthly_searches=300,
            fetched_at=now.replace(tzinfo=None), fresh_until=(now + timedelta(days=1)).replace(tzinfo=None),
        )
        db.add(evidence)
        db.flush()
        cache = ProviderCache(
            cache_key=provider_cache_key("mock", "search_volume", keyword=evidence.keyword),
            provider="mock", operation="historical_volume", evidence_type="search_volume",
            evidence_id=evidence.id, fetched_at=evidence.fetched_at, fresh_until=evidence.fresh_until,
        )
        db.add(cache)
        db.commit()
        assert cache.evidence_type == "search_volume"
        assert cache.evidence_id == evidence.id
        assert evidence_is_fresh(cache.fresh_until, now)
        assert not evidence_is_fresh((now - timedelta(days=1)).replace(tzinfo=None), now)
        assert db.get(SearchVolumeEvidence, evidence.id).avg_monthly_searches == 300


def test_provider_calls_distinguish_mock_zero_cost_cache_and_imports():
    engine = make_db()
    with Session(engine) as db:
        db.add_all([
            ProviderCall(provider="mock", stage="sv", operation="fetch", request_cache_key="a", outcome="success", source_kind="mock", actual_cost=0),
            ProviderCall(provider="mock", stage="sv", operation="reuse", request_cache_key="a", outcome="cache_hit", source_kind="cache", cache_hit=True, actual_cost=0),
            ImportBatch(source_kind="moz_csv", provider="moz", file_name="metrics.csv", row_count=2, accepted_count=2),
        ])
        db.commit()
        calls = db.query(ProviderCall).all()
        assert sum(c.actual_cost or 0 for c in calls) == 0
        assert not any(c.cache_hit and c.source_kind == "live_api" for c in calls)
        assert db.query(ImportBatch).one().source_kind == "moz_csv"


def test_authority_scope_keeps_domain_da_and_url_pa_distinct():
    engine = make_db()
    with Session(engine) as db:
        db.add_all([
            AuthorityEvidence(target_url="https://example.com/a", root_domain="example.com", target_type="URL", provider="mock", source_kind="mock", da=7, pa=22),
            AuthorityEvidence(target_url="https://example.com/b", root_domain="example.com", target_type="URL", provider="mock", source_kind="mock", da=7, pa=31),
        ])
        db.commit()
        rows = db.query(AuthorityEvidence).all()
        assert {r.da for r in rows} == {7}
        assert {r.pa for r in rows} == {22, 31}
