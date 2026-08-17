from dataclasses import dataclass


LOCAL_SCOPE = "LOCAL_RANK_RENT"
GENERAL_SCOPE = "GENERAL_NICHE"


@dataclass(frozen=True)
class ScopeDecision:
    scope: str
    reason: str
    requires_location: bool


def resolve_scope(*, location_target: dict | None, has_local_city_match: bool) -> ScopeDecision:
    """Classify once at handoff boundary; never invent a city for general terms."""
    target = location_target or {}
    explicit_city = bool(target.get("city") or target.get("city_id") or target.get("state_code"))
    if explicit_city:
        return ScopeDecision(LOCAL_SCOPE, "EXPLICIT_CITY_TARGET", True)
    if has_local_city_match:
        return ScopeDecision(LOCAL_SCOPE, "LOCAL_KEYWORD_MATCH", True)
    return ScopeDecision(GENERAL_SCOPE, "COUNTRY_TARGET_WITHOUT_LOCAL_MATCH", False)
