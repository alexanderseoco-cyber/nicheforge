from app.services.authority_evaluation import AuthorityEvaluationMode, evaluate_authority


def test_da_classification_defaults():
    assert evaluate_authority([5, 6, 7, 8], 4).primary_gate_result == "PASS"
    assert evaluate_authority([5, 6, 7, 8], 4).opportunity_classification == "PASS"
    assert evaluate_authority([5, 6, 7, 8, 9], 5).opportunity_classification == "IDEAL"
    assert evaluate_authority([20, 20, 20], 3).primary_gate_result == "PRIMARY_REJECTED"


def test_adaptive_preserves_unchecked_positions_and_full_evaluates_depth():
    adaptive = evaluate_authority([5, 6, 7, 8, 9, 20, 20, 20, 20, 20], 10, mode=AuthorityEvaluationMode.ADAPTIVE)
    full = evaluate_authority([5, 6, 7, 8, 9, 20, 20, 20, 20, 20], 10, mode=AuthorityEvaluationMode.FULL)
    assert adaptive.opportunity_classification == "IDEAL" and adaptive.authority_targets_evaluated == 5
    assert adaptive.unchecked_remaining == 5 and full.authority_targets_evaluated == 10


def test_adaptive_failure_is_mathematically_certain():
    result = evaluate_authority([20, 20, 20, 20, 20, 20, 20, None, None, None], 10)
    assert result.primary_gate_result == "PRIMARY_REJECTED" and result.unchecked_remaining == 3
