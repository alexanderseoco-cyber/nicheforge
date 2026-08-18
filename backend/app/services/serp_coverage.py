"""Authoritative SERP coverage policy and classification."""

from dataclasses import dataclass
from enum import StrEnum


class SerpEvidenceState(StrEnum):
    VALID = "VALID"
    PARTIAL_VALID = "PARTIAL_VALID"
    INSUFFICIENT = "INSUFFICIENT"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    INVALID_TARGET = "INVALID_TARGET"


@dataclass(frozen=True)
class SerpCoverage:
    evidence_state: SerpEvidenceState
    requested_depth: int
    usable_organic_count: int
    coverage_ratio: float
    sufficient_for_downstream: bool


def resolve_serp_policy(*, requested_depth: int, minimum_organic_rows: int | None, minimum_organic_coverage: float | None) -> tuple[int, float]:
    """Resolve persisted policy; null means legacy strict semantics."""
    if requested_depth <= 0:
        raise ValueError("organic_depth must be greater than zero")
    return (
        requested_depth if minimum_organic_rows is None else minimum_organic_rows,
        1.0 if minimum_organic_coverage is None else minimum_organic_coverage,
    )


def classify_serp_coverage(
    *,
    requested_depth: int,
    usable_organic_count: int,
    minimum_organic_rows: int | None = None,
    minimum_organic_coverage: float | None = None,
    provider_success: bool = True,
    invalid_target: bool = False,
) -> SerpCoverage:
    if requested_depth <= 0:
        return SerpCoverage(SerpEvidenceState.INVALID_TARGET, requested_depth, max(0, usable_organic_count), 0.0, False)
    requested = requested_depth
    observed = max(0, usable_organic_count)
    minimum_organic_rows, minimum_organic_coverage = resolve_serp_policy(requested_depth=requested, minimum_organic_rows=minimum_organic_rows, minimum_organic_coverage=minimum_organic_coverage)
    ratio = (observed / requested) if requested else 0.0
    if invalid_target:
        state = SerpEvidenceState.INVALID_TARGET
    elif not provider_success:
        state = SerpEvidenceState.PROVIDER_ERROR
    elif observed >= requested:
        state = SerpEvidenceState.VALID
    elif observed >= minimum_organic_rows and ratio >= minimum_organic_coverage:
        state = SerpEvidenceState.PARTIAL_VALID
    else:
        state = SerpEvidenceState.INSUFFICIENT
    return SerpCoverage(state, requested, observed, ratio, state in {SerpEvidenceState.VALID, SerpEvidenceState.PARTIAL_VALID})
