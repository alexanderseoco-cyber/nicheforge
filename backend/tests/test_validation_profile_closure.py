from app.schemas.domain import ValidationProfile
from app.services.gates import population_gate, search_volume_gate


def test_missing_enabled_sv_is_explicit_missing_evidence():
    decision = search_volume_gate(None, ValidationProfile(search_volume_enabled=True, min_search_volume=260))
    assert not decision.passed and decision.status == "MISSING_EVIDENCE"


def test_disabled_gates_are_not_applicable_not_fake_passes():
    profile = ValidationProfile(search_volume_enabled=False, population_enabled=False, min_search_volume=None)
    assert population_gate(1, profile).status == "NOT_APPLICABLE"
    assert search_volume_gate(None, profile).status == "NOT_APPLICABLE"


def test_profile_snapshot_is_immutable_for_historical_run_context():
    original = ValidationProfile(min_search_volume=260).model_dump()
    changed = ValidationProfile(min_search_volume=100).model_dump()
    assert original["min_search_volume"] == 260
    assert changed["min_search_volume"] == 100
    assert original != changed
