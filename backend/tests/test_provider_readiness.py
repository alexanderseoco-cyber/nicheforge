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
