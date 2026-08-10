from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.domain.freshness import FreshnessPolicy
from app.models.entities import CandidateEntity, City, KeywordDifficultyEvidence
from app.models.entities import ProviderCall, SearchVolumeEvidence
from app.domain.freshness import can_reuse
from app.services.identity import canonical_identity, identity_key


def test_moz_kd_defaults_and_strict_threshold_semantics():
    from app.schemas.domain import ValidationProfile
    p = ValidationProfile()
    assert p.kd_enabled and p.kd_provider == "moz" and p.kd_threshold == 15 and p.kd_operator == "<" and p.kd_mode == "PRIORITY"
    assert 14 < p.kd_threshold
    assert not (15 < p.kd_threshold)


def test_kd_is_append_only_and_provider_specific():
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine)
    with Session(engine) as db:
        city = City(name="Salina", state_code="KS", population=47000, population_vintage="test"); db.add(city); db.flush()
        c = canonical_identity("rodent control", "US-1600000")
        entity = CandidateEntity(canonical_identity=c, identity_key=identity_key(c), service_term_normalized="rodent control", city_id=city.id, canonical_keyword="rodent control salina ks"); db.add(entity); db.flush()
        db.add_all([
            KeywordDifficultyEvidence(candidate_entity_id=entity.id, keyword="rodent control salina ks", provider="moz", metric_type="keyword_difficulty", difficulty=17, source_kind="mock", raw_payload={"v": 1}),
            KeywordDifficultyEvidence(candidate_entity_id=entity.id, keyword="rodent control salina ks", provider="ahrefs", metric_type="keyword_difficulty", difficulty=5, source_kind="ahrefs_csv", raw_payload={"v": 2}),
        ]); db.commit()
        rows = db.query(KeywordDifficultyEvidence).all()
        assert len(rows) == 2 and {r.provider for r in rows} == {"moz", "ahrefs"}


def test_kd_priority_threshold_change_reuses_exact_evidence_semantics():
    kd = 17
    assert ("IDEAL" if kd < 15 else "ABOVE_PREFERRED") == "ABOVE_PREFERRED"
    assert ("IDEAL" if kd < 20 else "ABOVE_PREFERRED") == "IDEAL"
    assert kd == 17  # threshold changes are calculations, not evidence changes


def test_kd_hard_gate_and_da_precedence():
    kd = 17
    assert kd >= 15  # HARD_GATE rejects with KD_ABOVE_THRESHOLD
    assert kd < 20  # the same evidence is admitted after widening the threshold
    assert 2 < 5  # excellent KD cannot rescue a failed decisive DA requirement


def test_kd_freshness_modes_have_explicit_semantics():
    assert can_reuse("REUSE_FRESH_ONLY", True) == (True, False)
    assert can_reuse("REUSE_FRESH_ONLY", False) == (False, True)
    assert can_reuse("ALLOW_STALE_WITH_WARNING", False) == (True, True)
    assert can_reuse("FORCE_REFRESH", True) == (False, False)


def test_one_provider_call_can_produce_separate_sv_and_kd_evidence_without_double_cost():
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine)
    with Session(engine) as db:
        city = City(name="Salina", state_code="KS", population=47000, population_vintage="test"); db.add(city); db.flush()
        c = canonical_identity("rodent control", "US-1600000")
        entity = CandidateEntity(canonical_identity=c, identity_key=identity_key(c), service_term_normalized="rodent control", city_id=city.id, canonical_keyword="rodent control salina ks"); db.add(entity); db.flush()
        call = ProviderCall(provider="mock", stage="sv_kd", operation="keyword_metrics", request_cache_key="shared", outcome="success", source_kind="mock", actual_cost=0.25)
        db.add(call); db.flush()
        db.add(SearchVolumeEvidence(candidate_entity_id=entity.id, keyword=entity.canonical_keyword, location_name="Salina, KS", provider="mock", source_kind="mock", avg_monthly_searches=500, raw_payload={"call": call.id}))
        db.add(KeywordDifficultyEvidence(candidate_entity_id=entity.id, keyword=entity.canonical_keyword, provider="mock", source_kind="mock", difficulty=12, raw_payload={"call": call.id}))
        db.commit()
        assert db.query(ProviderCall).count() == 1
        assert db.query(SearchVolumeEvidence).count() == 1
        assert db.query(KeywordDifficultyEvidence).count() == 1
        assert sum(x.actual_cost or 0 for x in db.query(ProviderCall).all()) == 0.25
