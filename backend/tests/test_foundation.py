import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.entities import CandidateEntity, City
from app.services.identity import canonical_identity, identity_key
from app.domain.statuses import CandidateStatus, ReasonCode


def test_identity_is_deterministic_and_ignores_display_text():
    first = canonical_identity(" Rodent   Control ", "US-1600000", "EN", "us")
    second = canonical_identity("rodent control", "US-1600000", "en", "US")
    assert first == second
    assert identity_key(first) == identity_key(second)


def test_identity_changes_with_language_country_or_geography():
    base = canonical_identity("rodent control", "US-1600000")
    assert identity_key(base) != identity_key(canonical_identity("rodent control", "US-1600000", "es"))
    assert identity_key(base) != identity_key(canonical_identity("rodent control", "US-1600000", "en", "CA"))
    assert identity_key(base) != identity_key(canonical_identity("rodent control", "US-1600001"))


def test_canonical_statuses_and_reason_codes_are_defined():
    assert CandidateStatus.POPULATION_REJECTED.value == "POPULATION_REJECTED"
    assert CandidateStatus.PASS.value == "PASS"
    assert ReasonCode.LOW_DA_COUNT_BELOW_REQUIRED.value == "LOW_DA_COUNT_BELOW_REQUIRED"


def test_candidate_entity_identity_key_is_unique_and_model_is_creatable():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    assert "candidate_entities" in inspect(engine).get_table_names()
    canonical = canonical_identity("rodent control", "US-1600000")
    with Session(engine) as db:
        city = City(name="Salina", state_code="KS", population=47000, population_vintage="test")
        db.add(city)
        db.flush()
        db.add(CandidateEntity(
            canonical_identity=canonical,
            identity_key=identity_key(canonical),
            service_term_normalized="rodent control",
            city_id=city.id,
            canonical_keyword="rodent control salina ks",
        ))
        db.commit()
        assert db.query(CandidateEntity).count() == 1
        duplicate = CandidateEntity(
            canonical_identity=canonical,
            identity_key=identity_key(canonical),
            service_term_normalized="rodent control",
            city_id=city.id,
            canonical_keyword="different display text",
        )
        db.add(duplicate)
        with pytest.raises(IntegrityError):
            db.commit()
