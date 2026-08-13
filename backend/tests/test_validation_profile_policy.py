from app.schemas.domain import ValidationProfile
from app.services.gates import population_gate, search_volume_gate


def test_same_evidence_changes_decision_by_profile_without_provider_access():
    profiles=[ValidationProfile(min_search_volume=x) for x in (100,260,1000)]
    decisions=[search_volume_gate(300,p).passed for p in profiles]
    assert decisions == [True,True,False]


def test_profiles_can_disable_search_volume_and_population_independently():
    profile=ValidationProfile(search_volume_enabled=False, min_search_volume=None, population_enabled=False)
    assert search_volume_gate(None, profile).passed
    assert population_gate(1, profile).passed


def test_below_threshold_is_policy_status_not_invalid_evidence():
    decision = search_volume_gate(10, ValidationProfile(min_search_volume=260))
    assert decision.passed is False
    assert decision.status == "BELOW_SV_THRESHOLD"
    assert decision.reason_codes == ["SV_BELOW_THRESHOLD"]
