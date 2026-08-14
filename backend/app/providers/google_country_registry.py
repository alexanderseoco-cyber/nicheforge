"""Validated Google Ads country capability registry.

Criterion IDs are provider-owned values and must come from validated Google
Ads geo data; they must never be derived from ISO country codes.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CountryCapability:
    country_code: str
    status: str
    criterion_id: str | None = None
    provenance: str = "validated_project_registry"

    @property
    def resource_name(self) -> str | None:
        return f"geoTargetConstants/{self.criterion_id}" if self.criterion_id else None


VALIDATED_COUNTRY_CRITERION_IDS = {
    "US": "2840",
    "GB": "2826",
    "PK": "2586",
    "CA": "2124",
    "AU": "2036",
    "AE": "2784",
}


def country_capability(country_code: str) -> CountryCapability:
    code = (country_code or "").strip().upper()
    criterion_id = VALIDATED_COUNTRY_CRITERION_IDS.get(code)
    return CountryCapability(code, "SUPPORTED" if criterion_id else "UNSUPPORTED", criterion_id)


def country_resource(country_code: str) -> str:
    capability = country_capability(country_code)
    if capability.status != "SUPPORTED":
        raise ValueError(f"Google Ads country targeting is not supported for {capability.country_code or '<empty>'}")
    return capability.resource_name  # type: ignore[return-value]
