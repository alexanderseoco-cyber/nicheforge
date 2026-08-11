from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.entities import ManualMozObservation, SerpResultRow, SerpSnapshot
from app.services.serp_proxy import reconcile_manual_moz_domains


def _snapshot(db):
    snapshot = SerpSnapshot(candidate_id="pipeline", provider="dataforseo_trial", keyword="term")
    db.add(snapshot)
    db.flush()
    return snapshot


def test_reconciliation_matches_exact_domains_and_preserves_source_rank():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        snapshot = _snapshot(db)
        db.add_all([
            SerpResultRow(snapshot_id=snapshot.id, position=1, url="https://exact-one.com/page", root_domain="exact-one.com"),
            SerpResultRow(snapshot_id=snapshot.id, position=2, url="https://canonical-two.com", root_domain="canonical-two.com"),
        ])
        db.flush()
        validation = reconcile_manual_moz_domains(db, snapshot, {
            "exact-one.com": (7, 9), "other-three.com": (3, 1)
        })
        assert validation.positions_checked == 1
        assert validation.unavailable_positions == [2]
        assert validation.mismatched_domains == {"other-three.com": {"moz_da": 3, "source_rank": 1}}
        assert validation.moz_da_by_position["1"]["source_rank"] == 9
        assert validation.result == "REJECTED"
        assert db.scalar(select(ManualMozObservation).where(ManualMozObservation.normalized_domain == "exact-one.com"))


def test_reconciliation_reuses_observation_and_handles_duplicate_canonical_domains():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        snapshot = _snapshot(db)
        db.add_all([
            SerpResultRow(snapshot_id=snapshot.id, position=1, url="https://facebook.com/a", root_domain="facebook.com"),
            SerpResultRow(snapshot_id=snapshot.id, position=2, url="https://facebook.com/b", root_domain="facebook.com"),
        ])
        db.flush()
        observed = {"facebook.com": (96, 3)}
        first = reconcile_manual_moz_domains(db, snapshot, observed)
        second = reconcile_manual_moz_domains(db, snapshot, observed)
        assert first.positions_checked == second.positions_checked == 2
        assert len(db.scalars(select(ManualMozObservation)).all()) == 1
        assert second.validation_status == "COMPLETE"


def test_reconciliation_marks_partial_decisive_and_incomplete_correctly():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        decisive = _snapshot(db)
        for position in range(1, 5):
            db.add(SerpResultRow(snapshot_id=decisive.id, position=position, url=f"https://d{position}.com", root_domain=f"d{position}.com"))
        db.flush()
        result = reconcile_manual_moz_domains(db, decisive, {"d1.com": (10, 1)})
        assert result.validation_status == "PARTIAL_BUT_DECISIVE"
        assert result.result == "REJECTED"

        incomplete = _snapshot(db)
        for position in range(1, 5):
            db.add(SerpResultRow(snapshot_id=incomplete.id, position=position, url=f"https://i{position}.com", root_domain=f"i{position}.com"))
        db.flush()
        result = reconcile_manual_moz_domains(db, incomplete, {"i1.com": (4, 1)})
        assert result.validation_status == "INCOMPLETE"
        assert result.result == "INCOMPLETE"
