from datetime import datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.entities import (
    CandidateEntity, City, KeywordMetricEvidence, KeywordMetricValidationHandoff,
    Project, ProjectCandidate, Run, RunCandidate,
)
from app.services.identity import canonical_identity, identity_key
from app.services.run_pipeline import execute_run


def test_executor_uses_linked_keyword_metric_evidence_without_sv_provider(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    city = City(name="Albany", state_code="GA", population=47000, population_vintage="test")
    project = Project(name="E1 project")
    db.add_all([city, project]); db.flush()
    identity = canonical_identity("tree services", "US-1015247")
    entity = CandidateEntity(
        canonical_identity=identity, identity_key=identity_key(identity),
        service_term_normalized="tree services", city_id=city.id,
        canonical_keyword="tree services albany",
    )
    db.add(entity); db.flush()
    e1 = KeywordMetricEvidence(
        query_id="q-e1", submitted_keyword="tree services albany",
        provider_keyword="tree services albany", normalized_keyword="tree services albany",
        location_name="Albany, GA", location_target={"city": "Albany", "state": "GA"},
        language_code="en", country_code="US", provider="google_ads", source_kind="live_api",
        avg_monthly_searches=390, competition_index=12, monthly_history=[],
        raw_payload={"fixture": True}, fetched_at=datetime.utcnow(),
        fresh_until=datetime.utcnow() + timedelta(days=30),
    )
    db.add(e1); db.flush()
    handoff = KeywordMetricValidationHandoff(
        evidence_id=e1.id, submitted_keyword=e1.submitted_keyword,
        provider="google_ads", provider_keyword=e1.provider_keyword,
        location_target=e1.location_target, status="READY",
    )
    db.add(handoff); db.flush()
    pc = ProjectCandidate(
        project_id=project.id, candidate_entity_id=entity.id,
        search_volume_evidence_id=e1.id, display_keyword=e1.submitted_keyword,
        original_input=e1.submitted_keyword,
    )
    db.add(pc)
    run = Run(
        project_id=project.id, status="CREATED", min_population=20000,
        max_population=120000, min_search_volume=260, da_threshold=10,
        required_low_da_count=5, organic_depth=10, country_code="US",
        language_code="en", kd_enabled=False,
    )
    db.add(run); db.commit()
    before = db.scalar(select(KeywordMetricEvidence).count()) if False else db.query(KeywordMetricEvidence).count()

    class ForbiddenProvider:
        async def fetch(self, _requests):
            raise AssertionError("Google Ads Search Volume fallback was called")

    class ForbiddenSerp:
        async def fetch(self, _requests):
            raise AssertionError("SERP should not be part of this SV-stage proof")

    monkeypatch.setattr("app.services.run_pipeline.search_volume_provider", lambda: ForbiddenProvider())
    monkeypatch.setattr("app.services.run_pipeline.serp_provider", lambda: ForbiddenSerp())

    import asyncio
    asyncio.run(execute_run(db, run.id))
    rc = db.query(RunCandidate).filter_by(run_id=run.id, project_candidate_id=pc.id).one()
    assert rc.keyword_metric_evidence_id == e1.id
    assert rc.search_volume_evidence_id is None
    assert rc.status == "ERROR_RETRYABLE"
    assert any(event.event_type == "SV_PASSED" for event in db.query(__import__("app.models.entities", fromlist=["CandidateEvent"]).CandidateEvent).filter_by(run_candidate_id=rc.id))
    assert db.query(KeywordMetricEvidence).count() == before
    assert db.get(KeywordMetricEvidence, e1.id).avg_monthly_searches == 390
