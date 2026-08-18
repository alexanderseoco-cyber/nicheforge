"""Internal primary-authority decision boundary.

Evidence acquisition and persistence remain in the executor in order to keep
the existing flush, cache, and provider ordering unchanged.
"""

from dataclasses import dataclass

from app.providers.contracts import AuthorityResult
from app.services.authority_evaluation import AuthorityEvaluation, AuthorityEvaluationMode, evaluate_authority


@dataclass(frozen=True)
class AuthorityStageResult:
    metrics: tuple[AuthorityResult | None, ...]
    coverage_count: int
    observed_depth: int
    weak_da_count: int
    da_threshold: float
    evaluation: AuthorityEvaluation
    primary_gate_passed: bool


def evaluate_primary_authority(
    metrics: list[AuthorityResult | None],
    *,
    observed_depth: int,
    da_threshold: float,
    required_weak: int,
    ideal_weak: int,
    mode: AuthorityEvaluationMode,
    adaptive_seek_ideal: bool,
    cached_count: int,
    missing_count: int,
) -> AuthorityStageResult:
    """Normalize Moz/primary authority facts and preserve existing policy."""
    evaluation = evaluate_authority(
        [metric.da if metric else None for metric in metrics],
        observed_depth,
        required_weak,
        ideal_weak,
        da_threshold,
        mode,
        adaptive_seek_ideal,
        cached_count,
        missing_count,
    )
    coverage = sum(1 for metric in metrics if metric and metric.da is not None)
    weak = sum(1 for metric in metrics if metric and metric.da is not None and metric.da < da_threshold)
    passed = evaluation.primary_gate_result == "PASS"
    return AuthorityStageResult(tuple(metrics), coverage, observed_depth, weak, da_threshold, evaluation, passed)
