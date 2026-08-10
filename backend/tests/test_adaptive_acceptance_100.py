from statistics import median
from app.services.authority_evaluation import evaluate_authority, AuthorityEvaluationMode


def test_one_hundred_candidate_adaptive_vs_full_deterministic_comparison():
    adaptive = []
    full = []
    for index in range(100):
        values = ([5] * 5 + [20] * 5 if index % 4 == 0 else
                  [5] * 4 + [20] * 6 if index % 4 == 1 else
                  [20] * 10 if index % 4 == 2 else
                  [None, 5, 5, 5, 5, 20, 20, 20, 20, 20])
        adaptive.append(evaluate_authority(values, 10, mode=AuthorityEvaluationMode.ADAPTIVE))
        full.append(evaluate_authority(values, 10, mode=AuthorityEvaluationMode.FULL))
    evaluated_a = [item.authority_targets_evaluated for item in adaptive]
    evaluated_f = [item.authority_targets_evaluated for item in full]
    assert sum(evaluated_a) < sum(evaluated_f)
    assert all(item.unchecked_remaining >= 0 for item in adaptive)
    assert sum(item.opportunity_classification == "IDEAL" for item in adaptive) == 25
    assert sum(item.opportunity_classification == "PASS" for item in adaptive) == 50
    assert sum(item.primary_gate_result == "PRIMARY_REJECTED" for item in adaptive) == 25
    assert median(evaluated_a) <= 10
