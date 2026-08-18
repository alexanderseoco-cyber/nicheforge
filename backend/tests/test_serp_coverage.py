from app.services.serp_coverage import SerpEvidenceState, classify_serp_coverage


def test_serp_coverage_policy_matrix():
    assert classify_serp_coverage(requested_depth=10, usable_organic_count=10).evidence_state == SerpEvidenceState.VALID
    partial = classify_serp_coverage(requested_depth=10, usable_organic_count=9, minimum_organic_rows=9, minimum_organic_coverage=0.90)
    assert partial.evidence_state == SerpEvidenceState.PARTIAL_VALID
    assert partial.coverage_ratio == 0.9 and partial.sufficient_for_downstream
    insufficient = classify_serp_coverage(requested_depth=10, usable_organic_count=8, minimum_organic_rows=9, minimum_organic_coverage=0.90)
    assert insufficient.evidence_state == SerpEvidenceState.INSUFFICIENT
    assert classify_serp_coverage(requested_depth=10, usable_organic_count=0).evidence_state == SerpEvidenceState.INSUFFICIENT
    assert classify_serp_coverage(requested_depth=10, usable_organic_count=10, provider_success=False).evidence_state == SerpEvidenceState.PROVIDER_ERROR
    assert classify_serp_coverage(requested_depth=10, usable_organic_count=10, invalid_target=True).evidence_state == SerpEvidenceState.INVALID_TARGET
    assert classify_serp_coverage(requested_depth=0, usable_organic_count=0).evidence_state == SerpEvidenceState.INVALID_TARGET
