"""Target identity normalization for evidence compatibility checks."""

from typing import Any


def normalize_target(country_code: str | None, location_target: dict[str, Any] | None = None) -> str:
    """Return a stable identity without collapsing Worldwide into a country."""
    target = location_target or {}
    target_type = str(target.get("target_type") or "").strip().upper()
    country = str(country_code or target.get("country_code") or "").strip().upper()
    if target_type in {"WORLD", "WORLDWIDE", "GLOBAL"} or country in {"WORLD", "WORLDWIDE", "GLOBAL"}:
        return "WORLDWIDE"
    if target_type in {"CITY", "LOCAL_CITY"}:
        city_id = target.get("city_id") or target.get("geo_target_id") or target.get("resource_name")
        return f"CITY:{city_id or target.get('city') or target.get('city_name') or ''}"
    return country


def targets_compatible(evidence_country: str | None, evidence_target: dict[str, Any] | None, run_country: str | None, run_target: dict[str, Any] | None = None) -> bool:
    return normalize_target(evidence_country, evidence_target) == normalize_target(run_country, run_target)
