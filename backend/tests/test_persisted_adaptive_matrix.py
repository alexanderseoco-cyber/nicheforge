from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db.base import Base
from app.models.entities import Project, Run, RunCandidate
from app.services.authority_evaluation import evaluate_authority, AuthorityEvaluationMode


def test_persisted_adaptive_recalculation_matrix_and_restart(tmp_path: Path):
    db_path = tmp_path / "adaptive-matrix.sqlite"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        project = Project(name="matrix", profile_snapshot={}); db.add(project); db.flush()
        parent = Run(project_id=project.id, da_threshold=10, required_low_da_count=5, minimum_weak_domains=5,
                     ideal_weak_domains=6, authority_evaluation_mode="ADAPTIVE", authority_batch_size=2,
                     adaptive_seek_ideal=True, organic_depth=10, min_population=1, max_population=999999,
                     min_search_volume=0)
        child = Run(project_id=project.id, parent_run_id=parent.id, run_type="RECALCULATION", da_threshold=15,
                    required_low_da_count=4, minimum_weak_domains=4, ideal_weak_domains=5,
                    authority_evaluation_mode="FULL", authority_batch_size=5, adaptive_seek_ideal=False,
                    organic_depth=10, min_population=1, max_population=999999, min_search_volume=0)
        db.add(parent); db.flush(); child.parent_run_id = parent.id; db.add(child); db.flush()
        parent_rc = RunCandidate(run_id=parent.id, project_candidate_id="pc-parent", da_threshold_used=10,
                                 minimum_weak_domains_used=5, ideal_weak_domains_used=6,
                                 authority_evaluation_mode_used="ADAPTIVE", adaptive_seek_ideal_used=True,
                                 authority_targets_evaluated=6, authority_targets_cached=2,
                                 authority_targets_fetched=4, authority_targets_unchecked=4,
                                 confirmed_weak_count=4, opportunity_classification="FAIL", status="PRIMARY_REJECTED")
        child_rc = RunCandidate(run_id=child.id, project_candidate_id="pc-child", da_threshold_used=15,
                                minimum_weak_domains_used=4, ideal_weak_domains_used=5,
                                authority_evaluation_mode_used="FULL", adaptive_seek_ideal_used=False,
                                authority_targets_evaluated=10, authority_targets_cached=4,
                                authority_targets_fetched=6, authority_targets_unchecked=0,
                                confirmed_weak_count=5, opportunity_classification="PASS", status="PASS")
        db.add_all([parent_rc, child_rc]); db.commit()
        parent_id, child_id = parent.id, child.id
    engine.dispose()
    reopened = create_engine(f"sqlite:///{db_path}")
    with Session(reopened) as db:
        p, c = db.get(Run, parent_id), db.get(Run, child_id)
        assert p.da_threshold == 10 and p.minimum_weak_domains == 5 and p.ideal_weak_domains == 6
        assert p.authority_evaluation_mode == "ADAPTIVE" and p.authority_batch_size == 2 and p.adaptive_seek_ideal
        assert c.parent_run_id == p.id and c.da_threshold == 15 and c.minimum_weak_domains == 4
        assert c.authority_evaluation_mode == "FULL" and c.authority_batch_size == 5 and not c.adaptive_seek_ideal
        pr, cr = db.query(RunCandidate).filter_by(run_id=p.id).one(), db.query(RunCandidate).filter_by(run_id=c.id).one()
        assert (pr.authority_targets_evaluated, pr.authority_targets_unchecked, pr.confirmed_weak_count) == (6, 4, 4)
        assert (cr.authority_targets_evaluated, cr.authority_targets_unchecked, cr.confirmed_weak_count) == (10, 0, 5)
        assert pr.status == "PRIMARY_REJECTED" and cr.status == "PASS"
    reopened.dispose()


def test_threshold_and_seek_ideal_matrix_is_deterministic():
    values = [5, 5, 5, 5, 20, 20, 20, 20, 20, 20]
    assert evaluate_authority(values, 10, 5, 6).primary_gate_result == "PRIMARY_REJECTED"
    assert evaluate_authority(values, 10, 4, 5).opportunity_classification == "PASS"
    assert evaluate_authority([5] * 5 + [20] * 5, 10, 4, 5).opportunity_classification == "IDEAL"
    seeking = evaluate_authority(values, 10, 4, 5, mode=AuthorityEvaluationMode.ADAPTIVE, seek_ideal=True)
    stopping = evaluate_authority(values, 10, 4, 5, mode=AuthorityEvaluationMode.ADAPTIVE, seek_ideal=False)
    assert seeking.authority_targets_evaluated > stopping.authority_targets_evaluated
