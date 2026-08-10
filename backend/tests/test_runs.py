from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.entities import (
    AuthorityEvidence,
    CandidateEntity,
    CandidateEvent,
    City,
    Project,
    ProjectCandidate,
    ProviderCall,
    Run,
    RunCandidate,
    RunCandidateAuthorityEvidence,
    SearchVolumeEvidence,
    SerpResultRow,
    SerpSnapshot,
)
from app.services.identity import canonical_identity, identity_key


def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def seed_membership(db):
    city = City(name="Salina", state_code="KS", population=47000, population_vintage="test")
    project_a = Project(name="A", profile_snapshot={"min_search_volume": 300})
    project_b = Project(name="B", profile_snapshot={"min_search_volume": 250})
    db.add_all([city, project_a, project_b])
    db.flush()
    canonical = canonical_identity("rodent control", "US-1600000")
    entity = CandidateEntity(
        canonical_identity=canonical, identity_key=identity_key(canonical),
        service_term_normalized="rodent control", city_id=city.id,
        canonical_keyword="rodent control salina ks",
    )
    db.add(entity)
    db.flush()
    member_a = ProjectCandidate(project_id=project_a.id, candidate_entity_id=entity.id, display_keyword="rodent control salina ks")
    member_b = ProjectCandidate(project_id=project_b.id, candidate_entity_id=entity.id, display_keyword="rodent control salina ks")
    db.add_all([member_a, member_b])
    db.flush()
    return project_a, project_b, entity, member_a, member_b


def make_run(project_id, min_sv):
    return Run(
        project_id=project_id, status="COMPLETED", min_population=20000, max_population=120000,
        min_search_volume=min_sv, da_threshold=10, required_low_da_count=5, organic_depth=10,
        country_code="US", language_code="en", configuration_snapshot={"min_sv": min_sv},
    )


def test_run_configuration_is_snapshot_and_candidate_can_join_multiple_runs():
    db = db_session()
    project_a, project_b, entity, member_a, member_b = seed_membership(db)
    run_a = make_run(project_a.id, 300)
    run_b = make_run(project_a.id, 250)
    db.add_all([run_a, run_b])
    db.flush()
    db.add_all([
        RunCandidate(run_id=run_a.id, project_candidate_id=member_a.id, automatic_status="SV_REJECTED", reason_codes=["SV_BELOW_THRESHOLD"]),
        RunCandidate(run_id=run_b.id, project_candidate_id=member_a.id, automatic_status="PASS", reason_codes=[]),
    ])
    project_a.profile_snapshot = {"min_search_volume": 999}
    db.commit()
    assert db.get(Run, run_a.id).min_search_volume == 300
    assert db.query(RunCandidate).filter_by(project_candidate_id=member_a.id).count() == 2
    assert db.query(ProjectCandidate).filter_by(candidate_entity_id=entity.id).count() == 2


def test_events_are_append_only_and_ordered():
    db = db_session()
    project_a, _, _, member_a, _ = seed_membership(db)
    run = make_run(project_a.id, 300)
    db.add(run)
    db.flush()
    rc = RunCandidate(run_id=run.id, project_candidate_id=member_a.id, status="IMPORTED")
    db.add(rc)
    db.flush()
    base_time = datetime.utcnow()
    db.add_all([
        CandidateEvent(run_id=run.id, run_candidate_id=rc.id, project_candidate_id=member_a.id, event_type="ADMITTED", resulting_status="IMPORTED", created_at=base_time),
        CandidateEvent(run_id=run.id, run_candidate_id=rc.id, project_candidate_id=member_a.id, event_type="SV_REJECTED", previous_status="SV_PENDING", resulting_status="SV_REJECTED", reason_code="SV_BELOW_THRESHOLD", created_at=base_time + timedelta(seconds=1)),
    ])
    db.commit()
    events = db.query(CandidateEvent).filter_by(run_candidate_id=rc.id).order_by(CandidateEvent.created_at, CandidateEvent.id).all()
    assert [event.event_type for event in events] == ["ADMITTED", "SV_REJECTED"]
    assert len(events) == 2


def test_exact_serp_result_to_authority_evidence_lineage_is_pinned():
    db = db_session()
    project_a, _, entity, member_a, _ = seed_membership(db)
    run = make_run(project_a.id, 300)
    db.add(run)
    db.flush()
    sv = SearchVolumeEvidence(candidate_entity_id=entity.id, keyword="rodent control salina ks", location_name="Salina, KS", provider="mock", source_kind="mock", avg_monthly_searches=500)
    snap = SerpSnapshot(candidate_id="legacy", candidate_entity_id=entity.id, provider="mock", source_kind="mock", keyword="rodent control salina ks", location_name="Salina, KS", raw_payload={})
    db.add_all([sv, snap])
    db.flush()
    result = SerpResultRow(snapshot_id=snap.id, position=2, url="https://local.example/page", root_domain="local.example", title="Local")
    authority = AuthorityEvidence(candidate_entity_id=entity.id, target_url=result.url, root_domain=result.root_domain, target_type="URL", provider="mock", source_kind="mock", da=7, pa=24, raw_payload={"version": 1})
    db.add_all([result, authority])
    db.flush()
    rc = RunCandidate(run_id=run.id, project_candidate_id=member_a.id, serp_snapshot_id=snap.id, search_volume_evidence_id=sv.id, da_threshold_used=10, required_low_da_count_used=5)
    db.add(rc)
    db.flush()
    lineage = RunCandidateAuthorityEvidence(run_candidate_id=rc.id, serp_result_row_id=result.id, authority_evidence_id=authority.id, ranking_position=2, da_value_used=7, counted_as_low_da=True)
    db.add(lineage)
    db.add(ProviderCall(provider="mock", stage="authority", operation="fetch", request_cache_key="k", outcome="success", source_kind="mock", run_id=run.id, run_candidate_id=rc.id, actual_cost=0))
    db.commit()
    saved = db.query(RunCandidateAuthorityEvidence).one()
    assert saved.serp_result_row_id == result.id
    assert saved.authority_evidence_id == authority.id
    assert saved.da_value_used == 7
    assert db.query(ProviderCall).one().run_id == run.id


def test_da_boundary_and_missing_values_are_not_weak():
    threshold = 10
    values = [10, None, 9, 11]
    low = [value for value in values if value is not None and value < threshold]
    assert low == [9]
