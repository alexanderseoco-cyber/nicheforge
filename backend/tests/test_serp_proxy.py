from datetime import datetime

from app.db.base import Base
from app.models.entities import ProxyAuthorityEvidence, SerpResultRow, SerpSnapshot
from app.services.serp_proxy import evaluate_serp_proxy, persist_manual_moz_validation
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def test_serp_proxy_uses_minimum_and_maximum_counts_and_preserves_positions():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        snapshot = SerpSnapshot(candidate_id="pipeline", provider="dataforseo_trial", keyword="term", requested_depth=10)
        db.add(snapshot); db.flush()
        for position, dr in [(1, 2), (2, 20), (3, 80), (4, None)]:
            domain = f"site{position}-example.com"
            db.add(SerpResultRow(snapshot_id=snapshot.id, position=position, url=f"https://{domain}", root_domain=domain))
            if dr is not None:
                db.add(ProxyAuthorityEvidence(target_url=f"https://{domain}", root_domain=domain, provider="ahrefs", metric="domain_rating", domain_rating=dr, fetched_at=datetime.utcnow()))
        db.flush()
        evaluation = evaluate_serp_proxy(db, snapshot)
        assert evaluation.likely_weak_count == 1
        assert evaluation.possible_weak_count == 1
        assert evaluation.unknown_missing_count == 1
        assert evaluation.minimum_possible_weak == 1
        assert evaluation.maximum_plausible_weak == 3
        assert evaluation.classification == "SERP_PROXY_DATA_INCOMPLETE"


def test_serp_proxy_review_when_maximum_plausible_reaches_required_count():
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine)
    with Session(engine) as db:
        snapshot = SerpSnapshot(candidate_id="pipeline", provider="dataforseo_trial", keyword="term", requested_depth=10); db.add(snapshot); db.flush()
        for position, dr in enumerate([2, 3, 20, 80, 90], 1):
            domain = f"site{position}-example.com"; db.add(SerpResultRow(snapshot_id=snapshot.id, position=position, url=f"https://{domain}", root_domain=domain))
            db.add(ProxyAuthorityEvidence(target_url=f"https://{domain}", root_domain=domain, provider="ahrefs", metric="domain_rating", domain_rating=dr, fetched_at=datetime.utcnow()))
        db.flush(); evaluation = evaluate_serp_proxy(db, snapshot)
        assert evaluation.maximum_plausible_weak == 3
        assert evaluation.classification == "SERP_PROXY_REJECTED_HIGH_CONFIDENCE"
        for position in range(6, 7):
            domain=f"site{position}-example.com"; db.add(SerpResultRow(snapshot_id=snapshot.id, position=position, url=f"https://{domain}", root_domain=domain))
        db.flush(); evaluation = evaluate_serp_proxy(db, snapshot)
        assert evaluation.classification == "SERP_MOZ_REVIEW"


def test_manual_moz_validation_maps_serp_result():
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine)
    with Session(engine) as db:
        snapshot = SerpSnapshot(candidate_id="pipeline", provider="dataforseo_trial", keyword="term"); db.add(snapshot); db.flush()
        validation = persist_manual_moz_validation(db, snapshot, {"1": 4, "2": 9, "3": 10, "4": 2, "5": 7})
        assert validation.actual_da_below_10_count == 4
        assert validation.result == "PASS"
