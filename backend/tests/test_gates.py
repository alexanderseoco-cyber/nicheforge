from app.schemas.domain import ValidationProfile
from app.services.gates import population_gate, search_volume_gate, authority_gate


def test_population_gate():
    p = ValidationProfile(min_population=20000, max_population=120000)
    assert population_gate(50000, p).passed
    assert not population_gate(10000, p).passed
    assert not population_gate(130000, p).passed


def test_sv_gate_is_configurable():
    assert search_volume_gate(250, ValidationProfile(min_search_volume=250)).passed
    assert not search_volume_gate(249, ValidationProfile(min_search_volume=250)).passed


def test_primary_da_gate():
    p = ValidationProfile(da_threshold=10, required_low_da_count=5)
    decision, count = authority_gate([4, 7, 22, 3, 8, 41, 6, 11, 9, 70], p)
    assert count == 6
    assert decision.passed


def test_secondary_cannot_rescue_da_failure():
    p = ValidationProfile(da_threshold=10, required_low_da_count=5)
    decision, count = authority_gate([4, 7, 22, 30, 18, 41, 16, 11, 19, 70], p)
    assert count == 2
    assert not decision.passed
