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

    def validate_paid_execution(self, estimated_cost: float, approved: bool) -> None:
        if self.mode == ProviderMode.PRODUCTION and not self.production_enabled:
            raise ValueError("DataForSEO production mode is disabled")
        if estimated_cost > self.spend_ceiling:
            raise ValueError("Estimated provider cost exceeds configured spend ceiling")
        if self.mode != ProviderMode.SANDBOX and not approved:
            raise ValueError("Paid provider execution requires explicit approval")
