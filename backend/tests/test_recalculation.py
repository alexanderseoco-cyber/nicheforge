import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.db.base import Base

from app.models.entities import AuthorityEvidence, CandidateEvent, KeywordDifficultyEvidence, PopulationEvidence, ProviderCall, Run, RunCandidate, SearchVolumeEvidence, SerpSnapshot
from app.schemas.domain import ValidationProfile
from app.services.recalculation import candidate_history, create_recalculation, ledger, preview_recalculation, recalculate
from app.services.identity import canonical_identity, identity_key
from tests.test_pipeline import seeded_db


@pytest.mark.asyncio
async def test_lower_sv_threshold_creates_new_run_and_reuses_sv_evidence():
    db, run_a, candidate = seeded_db()
    run_a.min_search_volume = 100000
    db.commit()
    from app.services.run_pipeline import execute_run
    await execute_run(db, run_a.id, [candidate.id])
    profile = ValidationProfile(min_population=20000, max_population=120000, min_search_volume=0, da_threshold=10, required_low_da_count=0, organic_depth=10)
    preview = preview_recalculation(db, run_a.project_id, profile, [candidate.id])
    assert preview["total_affected"] == 1
    assert preview["sv_evidence_reusable"] == 1
    run_b = await recalculate(db, run_a.project_id, profile, parent_run_id=run_a.id, candidate_ids=[candidate.id])
    old = db.scalar(select(RunCandidate).where(RunCandidate.run_id == run_a.id))
    new = db.scalar(select(RunCandidate).where(RunCandidate.run_id == run_b.id))
    assert run_b.run_type == "RECALCULATION"
    assert run_b.parent_run_id == run_a.id
    assert old.status == "SV_REJECTED"
    assert new.status == "PASS"
    assert old.search_volume_evidence_id == new.search_volume_evidence_id
    assert db.query(ProviderCall).filter(ProviderCall.stage == "sv", ProviderCall.outcome == "success").count() == 1


@pytest.mark.asyncio
async def test_kd_threshold_recalculation_reuses_exact_evidence_without_new_provider_call():
    db, run_a, candidate = seeded_db()
    from app.services.run_pipeline import execute_run
    await execute_run(db, run_a.id, [candidate.id])
    old = db.scalar(select(RunCandidate).where(RunCandidate.run_id == run_a.id))
    evidence = db.get(KeywordDifficultyEvidence, old.keyword_difficulty_evidence_id)
    assert evidence is not None
    old_status = old.kd_status
    calls_before = db.query(ProviderCall).count()
    profile = ValidationProfile(
        min_population=20000, max_population=120000, min_search_volume=0,
        da_threshold=10, required_low_da_count=0, organic_depth=10,
        kd_enabled=True, kd_threshold=evidence.difficulty + 1, kd_mode="PRIORITY",
    )
    run_b = await recalculate(db, run_a.project_id, profile, parent_run_id=run_a.id, candidate_ids=[candidate.id])
    new = db.scalar(select(RunCandidate).where(RunCandidate.run_id == run_b.id))
    assert new.keyword_difficulty_evidence_id == old.keyword_difficulty_evidence_id
    assert new.kd_status == "IDEAL"
    assert db.query(ProviderCall).count() == calls_before + 1
    assert db.query(ProviderCall).filter_by(run_id=run_b.id, operation="PARENT_EVIDENCE_REUSE", http_request_count=0).count() == 1
    assert old.kd_status == old_status


@pytest.mark.asyncio
async def test_da_only_recalculation_reuses_serp_and_authority_lineage():
    db, run_a, candidate = seeded_db()
    from app.services.run_pipeline import execute_run
    run_a.required_low_da_count = 11
    db.commit()
    await execute_run(db, run_a.id, [candidate.id])
    old = db.scalar(select(RunCandidate).where(RunCandidate.run_id == run_a.id))
    old_lineage = db.query(__import__('app.models.entities', fromlist=['RunCandidateAuthorityEvidence']).RunCandidateAuthorityEvidence).filter_by(run_candidate_id=old.id).all()
    calls_before = db.query(ProviderCall).count()
    profile = ValidationProfile(min_population=20000, max_population=120000, min_search_volume=0, da_threshold=15, required_low_da_count=10, organic_depth=10, kd_enabled=False)
    run_b = await recalculate(db, run_a.project_id, profile, parent_run_id=run_a.id, candidate_ids=[candidate.id])
    new = db.scalar(select(RunCandidate).where(RunCandidate.run_id == run_b.id))
    new_lineage = db.query(__import__('app.models.entities', fromlist=['RunCandidateAuthorityEvidence']).RunCandidateAuthorityEvidence).filter_by(run_candidate_id=new.id).all()
    assert old.status == "PRIMARY_REJECTED" and new.status == "PASS"
    assert old.serp_snapshot_id == new.serp_snapshot_id
    assert [(x.ranking_position, x.authority_evidence_id) for x in old_lineage] == [(x.ranking_position, x.authority_evidence_id) for x in new_lineage]
    assert db.query(ProviderCall).count() == calls_before + 1
    assert db.query(ProviderCall).filter_by(run_id=run_b.id, operation="PARENT_EVIDENCE_REUSE", http_request_count=0).count() == 1
    assert old.required_low_da_count_used == 11 and new.required_low_da_count_used == 10
    assert new.minimum_weak_domains_used == 10
    assert new.ideal_weak_domains_used == profile.ideal_weak_domains
    assert new.authority_evaluation_mode_used == profile.authority_evaluation_mode
    assert new.adaptive_seek_ideal_used == profile.adaptive_seek_ideal
    assert new.authority_targets_evaluated == new.authority_results_available
    assert new.confirmed_weak_count == new.low_da_count


@pytest.mark.asyncio
async def test_adaptive_settings_recalculate_end_to_end_without_provider_calls():
    db, run_a, candidate = seeded_db()
    from app.services.run_pipeline import execute_run
    await execute_run(db, run_a.id, [candidate.id])
    old = db.scalar(select(RunCandidate).where(RunCandidate.run_id == run_a.id))
    calls_before = db.query(ProviderCall).count()
    profile = ValidationProfile(min_population=20000, max_population=120000, min_search_volume=0,
                                da_threshold=10, required_low_da_count=0, ideal_weak_domains=6,
                                authority_evaluation_mode="FULL", authority_batch_size=8,
                                adaptive_seek_ideal=False, organic_depth=10, kd_enabled=False)
    run_b = await recalculate(db, run_a.project_id, profile, parent_run_id=run_a.id, candidate_ids=[candidate.id])
    new = db.scalar(select(RunCandidate).where(RunCandidate.run_id == run_b.id))
    assert run_b.parent_run_id == run_a.id
    assert run_b.authority_evaluation_mode == "FULL" and run_b.authority_batch_size == 8
    assert not run_b.adaptive_seek_ideal
    assert old.authority_evaluation_mode_used == "ADAPTIVE"
    assert new.authority_evaluation_mode_used == "FULL"
    assert new.adaptive_seek_ideal_used is False
    assert new.serp_snapshot_id == old.serp_snapshot_id
    assert db.query(ProviderCall).count() == calls_before + 1
    assert db.query(ProviderCall).filter_by(run_id=run_b.id, operation="PARENT_EVIDENCE_REUSE", http_request_count=0).count() == 1
    assert new.authority_targets_evaluated == 10 and new.authority_targets_unchecked == 0


@pytest.mark.asyncio
async def test_preview_is_strictly_read_only_across_funnel_tables():
    db, run, candidate = seeded_db()
    from app.services.run_pipeline import execute_run
    await execute_run(db, run.id, [candidate.id])
    tables = [Run, RunCandidate, CandidateEvent, PopulationEvidence, SearchVolumeEvidence, KeywordDifficultyEvidence, SerpSnapshot, AuthorityEvidence, ProviderCall]
    before = {table.__tablename__: db.query(table).count() for table in tables}
    result = preview_recalculation(db, run.project_id, ValidationProfile(), [candidate.id])
    after = {table.__tablename__: db.query(table).count() for table in tables}
    assert before == after
    assert result["estimated_provider_calls"] >= 0
    assert "reusable_evidence_by_stage" in result


@pytest.mark.asyncio
async def test_current_summary_ignores_retryable_but_accepts_completed_rejection():
    db, run_a, candidate = seeded_db()
    from app.services.run_pipeline import execute_run
    await execute_run(db, run_a.id, [candidate.id])
    assert candidate.current_status == "PASS"
    retry = Run(project_id=run_a.project_id, run_type="STANDARD", min_population=20000, max_population=120000, min_search_volume=0, da_threshold=10, required_low_da_count=0, organic_depth=10)
    db.add(retry); db.flush()
    db.add(RunCandidate(run_id=retry.id, project_candidate_id=candidate.id, status="ERROR_RETRYABLE", reason_codes=["PROVIDER_ERROR"], finished_at=__import__('datetime').datetime.utcnow()))
    db.commit(); db.refresh(candidate)
    assert candidate.current_status == "PASS" and candidate.latest_run_id == run_a.id
    profile = ValidationProfile(min_population=20000, max_population=120000, min_search_volume=0, da_threshold=0, required_low_da_count=10, organic_depth=10, kd_enabled=False)
    rejected = await recalculate(db, run_a.project_id, profile, parent_run_id=run_a.id, candidate_ids=[candidate.id])
    db.refresh(candidate)
    assert candidate.current_status == "PRIMARY_REJECTED" and candidate.latest_run_id == rejected.id


@pytest.mark.asyncio
async def test_file_backed_restart_reconstructs_runs_evidence_lineage_ledger_and_history(tmp_path):
    path = tmp_path / "test-data" / "restart.sqlite3"
    path.parent.mkdir()
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        from tests.test_pipeline import seeded_db
        # Build the same durable fixture explicitly on the file-backed engine.
        from app.models.entities import CandidateEntity, City, Project, ProjectCandidate
        city = City(name="Salina", state_code="KS", population=47000, population_vintage="restart")
        project = Project(name="Restart", profile_snapshot={}); db.add_all([city, project]); db.flush()
        canonical = canonical_identity("rodent control", "US-1600000")
        entity = CandidateEntity(canonical_identity=canonical, identity_key=identity_key(canonical), service_term_normalized="rodent control", city_id=city.id, canonical_keyword="rodent control salina ks"); db.add(entity); db.flush()
        pc = ProjectCandidate(project_id=project.id, candidate_entity_id=entity.id, display_keyword=entity.canonical_keyword); db.add(pc); db.flush()
        run_a = Run(project_id=project.id, min_population=20000, max_population=120000, min_search_volume=0, da_threshold=10, required_low_da_count=0, organic_depth=10); db.add(run_a); db.commit()
        from app.services.run_pipeline import execute_run
        await execute_run(db, run_a.id, [pc.id])
        profile = ValidationProfile(min_population=20000, max_population=120000, min_search_volume=0, da_threshold=10, required_low_da_count=0, organic_depth=5)
        run_b = await recalculate(db, project.id, profile, parent_run_id=run_a.id, candidate_ids=[pc.id])
        run_a_id, run_b_id, pc_id = run_a.id, run_b.id, pc.id
    engine.dispose()
    reopened = create_engine(f"sqlite:///{path}")
    with Session(reopened) as db:
        a = db.get(Run, run_a_id); b = db.get(Run, run_b_id); current = db.get(__import__('app.models.entities', fromlist=['ProjectCandidate']).ProjectCandidate, pc_id)
        assert a and b and b.parent_run_id == a.id and current.latest_run_id == b.id
        a_rc = db.scalar(select(RunCandidate).where(RunCandidate.run_id == a.id)); b_rc = db.scalar(select(RunCandidate).where(RunCandidate.run_id == b.id))
        assert a_rc and b_rc and a_rc.population_evidence_id and a_rc.search_volume_evidence_id and a_rc.serp_snapshot_id and a_rc.keyword_difficulty_evidence_id
        assert b_rc.serp_snapshot_id == a_rc.serp_snapshot_id and b_rc.keyword_difficulty_evidence_id == a_rc.keyword_difficulty_evidence_id
        assert db.query(CandidateEvent).count() > 0 and db.query(ProviderCall).count() > 0
        assert ledger(db, current.project_id if hasattr(current, 'project_id') else a.project_id)["total"] == 1
        assert len(candidate_history(db, pc_id)["runs"]) == 2
    reopened.dispose()


def test_preview_does_not_create_runs_or_mutate_history():
    db, run, candidate = seeded_db()
    before = db.query(Run).count()
    result = preview_recalculation(db, run.project_id, ValidationProfile(), [candidate.id])
    assert result["total_affected"] == 1
    assert db.query(Run).count() == before
