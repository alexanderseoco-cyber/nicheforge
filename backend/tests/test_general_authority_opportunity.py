from app.services.authority_evaluation import evaluate_general_opportunity


def test_general_authority_is_graded_and_one_or_two_weak_domains_remain_viable():
    assert evaluate_general_opportunity([18, 19, 42, 55]).classification == "POTENTIAL_NICHE"
    assert "remains worth deeper review" in evaluate_general_opportunity([18, 19, 42, 55]).reason
    assert evaluate_general_opportunity([10, 11, 12, 13]).classification == "STRONG_POTENTIAL"
    assert evaluate_general_opportunity([10, 11, 12, 30]).classification == "GOOD_POTENTIAL"
    assert evaluate_general_opportunity([25, 30]).classification == "LOW_AUTHORITY_OPPORTUNITY"
