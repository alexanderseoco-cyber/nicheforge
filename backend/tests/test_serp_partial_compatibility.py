from types import SimpleNamespace

from app.services.evidence_compatibility import serp_snapshot_coverage


def _snapshot(rows, status=20000):
    return SimpleNamespace(requested_depth=10, raw_payload={"response": {"status_code": status}})


def test_partial_serp_cache_policy_matrix():
    assert serp_snapshot_coverage(_snapshot(10), observed_depth=10, requested_depth=10, minimum_organic_rows=9, minimum_organic_coverage=.90).evidence_state == "VALID"
    assert serp_snapshot_coverage(_snapshot(9), observed_depth=9, requested_depth=10, minimum_organic_rows=9, minimum_organic_coverage=.90).evidence_state == "PARTIAL_VALID"
    assert not serp_snapshot_coverage(_snapshot(9), observed_depth=9, requested_depth=10, minimum_organic_rows=10, minimum_organic_coverage=1.0).sufficient_for_downstream
    assert serp_snapshot_coverage(_snapshot(9), observed_depth=9, requested_depth=9, minimum_organic_rows=9, minimum_organic_coverage=1.0).evidence_state == "VALID"
    assert not serp_snapshot_coverage(_snapshot(8), observed_depth=8, requested_depth=10, minimum_organic_rows=9, minimum_organic_coverage=.90).sufficient_for_downstream
    assert serp_snapshot_coverage(_snapshot(9, 40501), observed_depth=9, requested_depth=10, minimum_organic_rows=9, minimum_organic_coverage=.90).evidence_state == "PROVIDER_ERROR"
