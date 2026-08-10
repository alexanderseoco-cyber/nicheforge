import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.entities import CandidateEntity, City, Project, ProjectCandidate, ProviderCall, Run, RunCandidate
from app.services.identity import canonical_identity, identity_key
from app.services.run_pipeline import execute_run


def seeded_db(population=47000, keyword="rodent control salina ks"):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    city = City(name="Salina", state_code="KS", population=population, population_vintage="test")
    project = Project(name="Pipeline", profile_snapshot={})
    db.add_all([city, project]); db.flush()
    canonical = canonical_identity("rodent control", "US-1600000")
    entity = CandidateEntity(canonical_identity=canonical, identity_key=identity_key(canonical), service_term_normalized="rodent control", city_id=city.id, canonical_keyword=keyword)
    db.add(entity); db.flush()
    candidate = ProjectCandidate(project_id=project.id, candidate_entity_id=entity.id, display_keyword=keyword)
    db.add(candidate); db.flush()
    run = Run(project_id=project.id, min_population=20000, max_population=120000, min_search_volume=0, da_threshold=10, required_low_da_count=0, organic_depth=10, configuration_snapshot={"test": True})
    db.add(run); db.commit()
    return db, run, candidate


@pytest.mark.asyncio
async def test_complete_mock_pipeline_persists_historical_result_and_counters():
    db, run, candidate = seeded_db()
    result = await execute_run(db, run.id, [candidate.id])
    rc = db.scalar(select(RunCandidate).where(RunCandidate.run_id == run.id))
    assert result.status == "COMPLETED"
    assert rc.serp_snapshot_id is not None
    assert rc.search_volume_evidence_id is not None
    assert rc.population_evidence_id is not None
    assert rc.status == "PASS"
    assert result.counters["primary_passed"] == 1


@pytest.mark.asyncio
async def test_population_rejection_stops_before_provider_calls():
    db, run, candidate = seeded_db(population=19999)
    result = await execute_run(db, run.id, [candidate.id])
    rc = db.scalar(select(RunCandidate).where(RunCandidate.run_id == run.id))
    assert rc.status == "POPULATION_REJECTED"
    assert rc.search_volume_evidence_id is None
    assert db.query(ProviderCall).count() == 0
    assert result.counters["population_rejected"] == 1


@pytest.mark.asyncio
async def test_sv_rejection_stops_before_serp_and_authority_calls():
    db, run, candidate = seeded_db()
    run.min_search_volume = 100000
    db.commit()
    await execute_run(db, run.id, [candidate.id])
    rc = db.scalar(select(RunCandidate).where(RunCandidate.run_id == run.id))
    assert rc.status == "SV_REJECTED"
    assert rc.serp_snapshot_id is None
    assert db.query(ProviderCall).filter(ProviderCall.stage.in_(["serp", "authority"])).count() == 0


@pytest.mark.asyncio
async def test_reexecution_of_completed_run_is_idempotent():
    db, run, candidate = seeded_db()
    await execute_run(db, run.id, [candidate.id])
    first_rc_count = db.query(RunCandidate).count()
    first_events = db.query(__import__('app.models.entities', fromlist=['CandidateEvent']).CandidateEvent).count()
    await execute_run(db, run.id, [candidate.id])
    assert db.query(RunCandidate).count() == first_rc_count
    assert db.query(__import__('app.models.entities', fromlist=['CandidateEvent']).CandidateEvent).count() == first_events
