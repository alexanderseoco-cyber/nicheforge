from dataclasses import dataclass
from enum import StrEnum


class ProviderMode(StrEnum):
    SANDBOX = "SANDBOX"
    TRIAL = "TRIAL"
    PRODUCTION = "PRODUCTION"


@dataclass(frozen=True)
class DataForSEOConfig:
    mode: ProviderMode = ProviderMode.SANDBOX
    standard_serp_cost: float = 0.0
    spend_ceiling: float = 0.0
    remaining_trial_budget: float | None = None
    production_enabled: bool = False
    credentials_configured: bool = False
    provider_enabled: bool = True

    @classmethod
    def from_settings(cls, settings):
        return cls(mode=ProviderMode(settings.dataforseo_mode.upper()),
                   remaining_trial_budget=settings.dataforseo_trial_budget,
                   standard_serp_cost=settings.dataforseo_serp_estimated_cost,
                   credentials_configured=bool(settings.dataforseo_login and settings.dataforseo_password),
                   provider_enabled=settings.dataforseo_provider_enabled)

    def validate_paid_execution(self, estimated_cost: float, approved: bool) -> None:
        if not self.provider_enabled:
            raise ValueError("DataForSEO provider is disabled")
        if self.mode != ProviderMode.SANDBOX and not self.credentials_configured:
            raise ValueError("DataForSEO credentials are not configured")
        if self.mode == ProviderMode.PRODUCTION and not self.production_enabled:
            raise ValueError("DataForSEO production mode is disabled")
        budget = self.remaining_trial_budget if self.remaining_trial_budget is not None else self.spend_ceiling
        if estimated_cost > budget:
            raise ValueError("Estimated provider cost exceeds configured spend ceiling")
        if self.mode != ProviderMode.SANDBOX and not approved:
            raise ValueError("Paid provider execution requires explicit approval")
