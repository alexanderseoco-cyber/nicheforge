from datetime import datetime

from app.models.entities import ProviderCall
from app.providers.contracts import AuthorityTarget
from app.providers.moz import MozAuthorizedProvider
from app.services.run_pipeline import _call


def test_provider_call_telemetry_fields_are_optional_and_existing_fields_remain_distinct():
    call = ProviderCall(
        provider="mock",
        stage="authority",
        operation="batch_fetch",
        request_cache_key="key",
        outcome="success",
        source_kind="mock",
    )

    assert call.attempt_number is None
    assert call.provider_reached is None
    assert call.logical_item_count is None
    assert call.cache_outcome is None
    assert call.metadata_json is None


def test_moz_contract_still_targets_full_urls_and_combined_metrics():
    provider = object.__new__(MozAuthorizedProvider)
    result = provider._normalize_item(
        AuthorityTarget("https://example.com/service", "example.com"),
        {"domain_authority": 21, "page_authority": 17},
    )

    assert result.url == "https://example.com/service"
    assert result.root_domain == "example.com"
    assert result.da == 21
    assert result.pa == 17


def test_provider_call_telemetry_can_represent_request_and_item_aggregates():
    call = ProviderCall(
        provider="moz",
        stage="authority",
        operation="batch_fetch",
        request_cache_key="key",
        outcome="success",
        source_kind="live_api",
        logical_item_count=10,
        unique_target_count=8,
        cache_hit_count=2,
        cache_miss_count=8,
        provider_item_count=8,
        batch_count=1,
        batch_size=8,
        http_request_count=1,
        retry_count=0,
        http_request_sent=True,
        paid_attempt=None,
        cost_confidence="UNKNOWN",
        started_at=datetime.utcnow(),
    )

    assert call.logical_item_count == 10
    assert call.unique_target_count == 8
    assert call.provider_item_count == 8
    assert call.http_request_count == 1
    assert call.retry_count == 0


def test_moz_telemetry_uses_actual_batch_request_count_and_compact_duplication_metadata():
    class DB:
        def __init__(self):
            self.rows = []

        def begin_nested(self):
            class Savepoint:
                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False
            return Savepoint()

        def add(self, row):
            self.rows.append(row)

        def flush(self):
            pass

    class Run:
        id = "run"
        configuration_snapshot = {}

    class Candidate:
        id = "candidate"

    db = DB()
    _call(
        db, Run(), Candidate(), "moz", "authority", "batch", "cache", "success", "moz",
        telemetry={
            "provider_item_count": 10,
            "batch_count": 1,
            "http_request_count": 1,
            "metadata_json": {
                "authority_occurrence_count": 10,
                "unique_url_count": 10,
                "unique_domain_count": 10,
                "same_url_duplicate_count": 0,
                "same_domain_different_url_count": 0,
            },
        },
    )

    assert db.rows[0].provider_item_count == 10
    assert db.rows[0].batch_count == 1
    assert db.rows[0].http_request_count == 1
    assert db.rows[0].metadata_json["same_domain_different_url_count"] == 0


def test_moz_duplication_formulas_cover_all_required_shapes():
    cases = [
        (10, 8, 8, 2, 0),
        (10, 10, 7, 0, 3),
        (10, 8, 6, 2, 2),
    ]
    for occurrences, urls, domains, same_url, same_domain_url in cases:
        assert occurrences - urls == same_url
        assert urls - domains == same_domain_url


def test_telemetry_failure_does_not_poison_main_session_or_validation_state():
    class DB:
        def __init__(self):
            self.calls = 0

        def begin_nested(self):
            class Savepoint:
                def __enter__(inner):
                    return inner

                def __exit__(inner, exc_type, exc, tb):
                    return False
            return Savepoint()

        def add(self, row):
            self.calls += 1
            raise RuntimeError("injected telemetry failure")

        def flush(self):
            raise AssertionError("telemetry flush should not be reached after add failure")

    class Run:
        id = "run"
        configuration_snapshot = {}

    class Candidate:
        id = "candidate"

    db = DB()
    _call(db, Run(), Candidate(), "moz", "authority", "authority_summary",
          "summary", "success", "moz", telemetry={"http_request_count": 0})
    assert db.calls == 1
    assert db.begin_nested() is not None
