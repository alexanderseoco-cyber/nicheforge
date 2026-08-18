from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.entities import City, ProviderLocationIdentity
from app.services.provider_location_registry import (
    ProviderLocationUnresolved,
    find_verified_mapping,
    persist_verified_mapping,
    require_verified_mapping,
)


def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def city(db, name="Albany", state="NY"):
    value = City(name=name, state_code=state, population=100000, population_vintage="2025")
    db.add(value); db.flush()
    return value


def test_verified_mapping_is_persistent_and_exact():
    db = db_session(); ny = city(db)
    persist_verified_mapping(db, ny, provider="dataforseo", location_code=101, provider_location_name="Albany, New York, United States", fetched_at=datetime.utcnow())
    db.commit()
    assert require_verified_mapping(db, ny).location_code == 101


def test_same_city_name_different_state_does_not_match():
    db = db_session(); ny = city(db); ga = city(db, state="GA")
    persist_verified_mapping(db, ny, provider="dataforseo", location_code=101, provider_location_name="Albany, New York, United States")
    db.commit()
    assert find_verified_mapping(db, ga, "dataforseo") is None


def test_unverified_and_wrong_provider_are_rejected():
    db = db_session(); ny = city(db)
    db.add(ProviderLocationIdentity(city_id=ny.id, provider="dataforseo", location_code=101, provider_location_name="Albany, New York, United States", country_code="US", state_code="NY", city_name="Albany", location_type="City", source="IMPORTED", verified=False, created_at=datetime.utcnow(), updated_at=datetime.utcnow()))
    db.commit()
    assert find_verified_mapping(db, ny, "dataforseo") is None
    with pytest.raises(ProviderLocationUnresolved):
        require_verified_mapping(db, ny, "dataforseo")


def test_duplicate_provider_city_and_code_are_rejected():
    db = db_session(); ny = city(db); ga = city(db, state="GA")
    persist_verified_mapping(db, ny, provider="dataforseo", location_code=101, provider_location_name="Albany, New York, United States")
    db.commit()
    with pytest.raises(Exception):
        persist_verified_mapping(db, ny, provider="dataforseo", location_code=102, provider_location_name="Albany, New York, United States")
    db.rollback()
    with pytest.raises(Exception):
        persist_verified_mapping(db, ga, provider="dataforseo", location_code=101, provider_location_name="Albany, Georgia, United States")
