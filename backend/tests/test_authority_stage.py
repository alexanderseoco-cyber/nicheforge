from app.providers.contracts import AuthorityResult
from app.services.authority_evaluation import AuthorityEvaluationMode
from app.services.authority_stage import evaluate_primary_authority


def test_primary_authority_preserves_coverage_weak_count_and_threshold():
    result = evaluate_primary_authority(
        [AuthorityResult("https://a.test", "a.test", 5, 10), None, AuthorityResult("https://c.test", "c.test", 30, 20)],
        serp_count=3, da_threshold=20, required_weak=1, ideal_weak=2,
        mode=AuthorityEvaluationMode.FULL, adaptive_seek_ideal=False,
        cached_count=1, missing_count=2,
    )
    assert result.coverage_count == 2
    assert result.weak_da_count == 1
    assert result.da_threshold == 20
    assert result.serp_count == 3


def test_primary_authority_does_not_turn_missing_da_into_zero():
    result = evaluate_primary_authority(
        [AuthorityResult("https://a.test", "a.test", None, None)],
        serp_count=1, da_threshold=20, required_weak=1, ideal_weak=1,
        mode=AuthorityEvaluationMode.FULL, adaptive_seek_ideal=False,
        cached_count=0, missing_count=1,
    )
    assert result.coverage_count == 0
    assert result.weak_da_count == 0
    assert result.metrics[0].da is None
