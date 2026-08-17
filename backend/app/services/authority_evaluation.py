from dataclasses import dataclass
from enum import StrEnum


class AuthorityEvaluationMode(StrEnum):
    FULL = "FULL"
    ADAPTIVE = "ADAPTIVE"


@dataclass(frozen=True)
class AuthorityEvaluation:
    organic_depth: int
    authority_targets_evaluated: int
    authority_targets_cached: int
    authority_targets_fetched: int
    unchecked_remaining: int
    confirmed_weak_count: int
    minimum_weak_domains: int
    ideal_weak_domains: int
    primary_gate_result: str
    opportunity_classification: str


@dataclass(frozen=True)
class GeneralAuthorityOpportunity:
    weak_count: int
    evaluated_count: int
    threshold: float
    classification: str
    reason: str


def evaluate_general_opportunity_metrics(da_values: list[float | None], dr_values: list[float | None], threshold: float = 20.0) -> GeneralAuthorityOpportunity:
    da_weak = sum(value is not None and value < threshold for value in da_values)
    dr_weak = sum(value is not None and value < threshold for value in dr_values)
    unique_weak = sum((da is not None and da < threshold) or (dr is not None and dr < threshold) for da, dr in zip(da_values, dr_values))
    if unique_weak >= 4: classification = "STRONG_POTENTIAL"
    elif unique_weak == 3: classification = "GOOD_POTENTIAL"
    elif unique_weak >= 1: classification = "POTENTIAL_NICHE"
    else: classification = "LOW_AUTHORITY_OPPORTUNITY"
    reason = f"{unique_weak} unique ranking domains meet DA < {threshold:g} or DR < {threshold:g}; {da_weak} DA records and {dr_weak} DR records are below threshold."
    if 1 <= unique_weak <= 2: reason += " The opportunity remains worth deeper review despite being below the preferred 3–4 weak-domain range."
    return GeneralAuthorityOpportunity(unique_weak, sum(da is not None or dr is not None for da, dr in zip(da_values, dr_values)), threshold, classification, reason)


def evaluate_general_opportunity(da_values: list[float | None], threshold: float = 20.0) -> GeneralAuthorityOpportunity:
    observed = [value for value in da_values if value is not None]
    weak = sum(value < threshold for value in observed)
    if weak >= 4:
        classification = "STRONG_POTENTIAL"
    elif weak == 3:
        classification = "GOOD_POTENTIAL"
    elif weak >= 1:
        classification = "POTENTIAL_NICHE"
    else:
        classification = "LOW_AUTHORITY_OPPORTUNITY"
    reason = f"{weak} of {len(observed)} evaluated ranking domains have DA below {threshold:g}."
    if 1 <= weak <= 2:
        reason += " The opportunity is below the preferred 3–4 weak-domain range but remains worth deeper review."
    return GeneralAuthorityOpportunity(weak, len(observed), threshold, classification, reason)


def evaluate_authority(da_values: list[float | None], organic_depth: int, minimum_weak_domains: int = 4,
                       ideal_weak_domains: int = 5, da_threshold: float = 10.0,
                       mode: AuthorityEvaluationMode = AuthorityEvaluationMode.ADAPTIVE,
                       seek_ideal: bool = True,
                       cached_count: int = 0, fetched_count: int = 0) -> AuthorityEvaluation:
    """Evaluate only observed authority values; None positions remain unchecked."""
    values = da_values[:organic_depth] if mode == AuthorityEvaluationMode.FULL else da_values[:organic_depth]
    weak = 0; evaluated = 0; stop_at = len(values)
    for index, value in enumerate(values):
        if value is None: continue
        evaluated += 1; weak += int(value < da_threshold)
        remaining = organic_depth - index - 1
        if (not seek_ideal and weak >= minimum_weak_domains) or weak >= ideal_weak_domains or weak >= minimum_weak_domains and weak + remaining < ideal_weak_domains or weak + remaining < minimum_weak_domains:
            stop_at = index + 1
            if mode == AuthorityEvaluationMode.ADAPTIVE: break
    observed = values[:stop_at] if mode == AuthorityEvaluationMode.ADAPTIVE else values
    weak = sum(1 for value in observed if value is not None and value < da_threshold)
    evaluated = sum(value is not None for value in observed)
    unchecked = max(0, organic_depth - evaluated)
    if weak >= ideal_weak_domains: result = ("PASS", "IDEAL")
    elif weak >= minimum_weak_domains: result = ("PASS", "PASS")
    elif weak + unchecked < minimum_weak_domains: result = ("PRIMARY_REJECTED", "FAIL")
    else: result = ("ERROR_RETRYABLE", "UNDETERMINED")
    return AuthorityEvaluation(organic_depth, evaluated, cached_count, fetched_count, unchecked, weak, minimum_weak_domains, ideal_weak_domains, *result)
