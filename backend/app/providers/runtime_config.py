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
    production_enabled: bool = False
    credentials_configured: bool = False
    provider_enabled: bool = True

    def validate_paid_execution(self, estimated_cost: float, approved: bool) -> None:
        if not self.provider_enabled:
            raise ValueError("DataForSEO provider is disabled")
        if self.mode != ProviderMode.SANDBOX and not self.credentials_configured:
            raise ValueError("DataForSEO credentials are not configured")
        if self.mode == ProviderMode.PRODUCTION and not self.production_enabled:
            raise ValueError("DataForSEO production mode is disabled")
        if estimated_cost > self.spend_ceiling:
            raise ValueError("Estimated provider cost exceeds configured spend ceiling")
        if self.mode != ProviderMode.SANDBOX and not approved:
            raise ValueError("Paid provider execution requires explicit approval")
