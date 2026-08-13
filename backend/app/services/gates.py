from dataclasses import dataclass
from app.schemas.domain import ValidationProfile


@dataclass
class GateDecision:
    passed: bool
    reason_codes: list[str]
    status: str = "APPLIED"


def population_gate(population: int, profile: ValidationProfile) -> GateDecision:
    if not profile.population_enabled:
        return GateDecision(True, ["POPULATION_NOT_APPLICABLE"], "NOT_APPLICABLE")
    if population < profile.min_population:
        return GateDecision(False, ["POPULATION_BELOW_MIN"])
    if population > profile.max_population:
        return GateDecision(False, ["POPULATION_ABOVE_MAX"])
    return GateDecision(True, [])


def search_volume_gate(search_volume: int | None, profile: ValidationProfile) -> GateDecision:
    if not profile.search_volume_enabled or profile.min_search_volume is None:
        return GateDecision(True, ["SV_NOT_APPLICABLE"], "NOT_APPLICABLE")
    if search_volume is None:
        return GateDecision(False, ["SV_MISSING"], "MISSING_EVIDENCE")
    if search_volume < profile.min_search_volume:
        return GateDecision(False, ["SV_BELOW_THRESHOLD"], "BELOW_SV_THRESHOLD")
    return GateDecision(True, [])


def authority_gate(da_values: list[float | None], profile: ValidationProfile) -> tuple[GateDecision, int]:
    available = [x for x in da_values[:profile.organic_depth] if x is not None]
    if len(available) < min(profile.organic_depth, profile.required_low_da_count):
        return GateDecision(False, ["AUTHORITY_DATA_INCOMPLETE"]), 0
    count = sum(1 for x in available if x < profile.da_threshold)
    if count < profile.required_low_da_count:
        return GateDecision(False, ["LOW_DA_COUNT_BELOW_REQUIRED"]), count
    return GateDecision(True, []), count
