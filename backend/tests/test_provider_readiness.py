import pytest
from app.providers.runtime_config import DataForSEOConfig, ProviderMode


def test_dataforseo_sandbox_is_default_and_free():
    config = DataForSEOConfig()
    assert config.mode == ProviderMode.SANDBOX and config.standard_serp_cost == 0
    config.validate_paid_execution(0, False)


def test_production_disabled_and_trial_requires_budget_approval():
    with pytest.raises(ValueError): DataForSEOConfig(mode=ProviderMode.PRODUCTION).validate_paid_execution(0.01, True)
    with pytest.raises(ValueError): DataForSEOConfig(mode=ProviderMode.TRIAL, spend_ceiling=0.01).validate_paid_execution(0.02, True)
    with pytest.raises(ValueError): DataForSEOConfig(mode=ProviderMode.TRIAL, spend_ceiling=1).validate_paid_execution(0.01, False)


def test_trial_budget_boundary_and_historical_configuration_immutability():
    run_a_config = DataForSEOConfig(mode=ProviderMode.TRIAL, remaining_trial_budget=1.0, standard_serp_cost=0.10, credentials_configured=True)
    run_a_config.validate_paid_execution(1.0, True)
    DataForSEOConfig(mode=ProviderMode.TRIAL, remaining_trial_budget=1.0, credentials_configured=True).validate_paid_execution(0.99, True)
    with pytest.raises(ValueError):
        DataForSEOConfig(mode=ProviderMode.TRIAL, remaining_trial_budget=1.0, credentials_configured=True).validate_paid_execution(1.01, True)
    # A copied Run snapshot is not mutated when future configuration changes.
    snapshot = {"remaining_trial_budget": run_a_config.remaining_trial_budget, "standard_serp_cost": run_a_config.standard_serp_cost}
    future = DataForSEOConfig(mode=ProviderMode.TRIAL, remaining_trial_budget=2.0, standard_serp_cost=0.20, credentials_configured=True)
    assert snapshot == {"remaining_trial_budget": 1.0, "standard_serp_cost": 0.10}
    future.validate_paid_execution(2.0, True)


def test_paid_guards_are_independent():
    with pytest.raises(ValueError):
        DataForSEOConfig(mode=ProviderMode.TRIAL, remaining_trial_budget=2, credentials_configured=False).validate_paid_execution(1, True)
    with pytest.raises(ValueError):
        DataForSEOConfig(mode=ProviderMode.TRIAL, remaining_trial_budget=2, credentials_configured=True, provider_enabled=False).validate_paid_execution(1, True)
