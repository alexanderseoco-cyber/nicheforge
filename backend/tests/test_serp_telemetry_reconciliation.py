from app.services.serp_coverage import classify_serp_coverage, SerpEvidenceState
from app.models.entities import ProviderCall
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base


def test_serp_coverage_states_remain_canonical():
    assert classify_serp_coverage(requested_depth=10, usable_organic_count=10).evidence_state == SerpEvidenceState.VALID
    assert classify_serp_coverage(requested_depth=10, usable_organic_count=9, minimum_organic_rows=9, minimum_organic_coverage=.90).evidence_state == SerpEvidenceState.PARTIAL_VALID
    assert classify_serp_coverage(requested_depth=10, usable_organic_count=8, minimum_organic_rows=9, minimum_organic_coverage=.90).evidence_state == SerpEvidenceState.INSUFFICIENT
    assert classify_serp_coverage(requested_depth=10, usable_organic_count=0, provider_success=False).evidence_state == SerpEvidenceState.PROVIDER_ERROR
    assert classify_serp_coverage(requested_depth=0, usable_organic_count=0).evidence_state == SerpEvidenceState.INVALID_TARGET


def test_serp_operation_categories_aggregate_without_double_counting():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add_all([
        ProviderCall(provider="dataforseo", stage="serp", operation="PROVIDER_ACQUISITION", request_cache_key="valid", outcome="success", source_kind="dataforseo", logical_item_count=1, unique_target_count=1, provider_item_count=1, batch_count=1, http_request_count=1, http_request_sent=True, paid_attempt=False, items_returned_count=1, evidence_created_count=1, cost_confidence="UNKNOWN", actual_cost=None, estimated_cost=None, currency=None, metadata_json={"evidence_state": "VALID"}),
        ProviderCall(provider="dataforseo", stage="serp", operation="PROVIDER_ACQUISITION", request_cache_key="partial", outcome="success", source_kind="dataforseo", logical_item_count=1, unique_target_count=1, provider_item_count=1, batch_count=1, http_request_count=1, http_request_sent=True, paid_attempt=False, items_returned_count=1, evidence_created_count=1, evidence_partial_count=1, cost_confidence="UNKNOWN", actual_cost=None, estimated_cost=None, currency=None, metadata_json={"evidence_state": "PARTIAL_VALID"}),
        ProviderCall(provider="dataforseo", stage="serp", operation="PROVIDER_ACQUISITION", request_cache_key="error", outcome="error", source_kind="dataforseo", logical_item_count=1, unique_target_count=1, provider_item_count=1, batch_count=1, http_request_count=1, http_request_sent=True, paid_attempt=False, items_returned_count=0, evidence_missing_count=1, cost_confidence="UNKNOWN", actual_cost=None, estimated_cost=None, currency=None, metadata_json={"evidence_state": "PROVIDER_ERROR"}),
        ProviderCall(provider="dataforseo", stage="serp", operation="CACHE_REUSE", request_cache_key="reuse", outcome="cache_hit", source_kind="cache", logical_item_count=1, unique_target_count=1, provider_item_count=0, batch_count=0, http_request_count=0, http_request_sent=False, paid_attempt=False, evidence_reused_count=1, actual_evidence_provider="dataforseo", cost_confidence="NOT_APPLICABLE", actual_cost=None, estimated_cost=None, currency=None, metadata_json={"evidence_state": "PARTIAL_VALID"}),
        ProviderCall(provider="dataforseo", stage="serp", operation="PARENT_EVIDENCE_REUSE", request_cache_key="parent", outcome="reuse", source_kind="parent_evidence", logical_item_count=1, unique_target_count=1, provider_item_count=0, batch_count=0, http_request_count=0, http_request_sent=False, paid_attempt=False, evidence_reused_count=1, actual_evidence_provider="dataforseo", cost_confidence="NOT_APPLICABLE", actual_cost=None, estimated_cost=None, currency=None),
    ])
    db.flush()
    acquisition = db.query(ProviderCall).filter(ProviderCall.operation == "PROVIDER_ACQUISITION").all()
    reuse = db.query(ProviderCall).filter(ProviderCall.operation == "CACHE_REUSE").all()
    parent = db.query(ProviderCall).filter(ProviderCall.operation == "PARENT_EVIDENCE_REUSE").all()
    assert len(acquisition) == 3 and sum(r.http_request_count for r in acquisition) == 3
    assert sum(r.evidence_reused_count or 0 for r in reuse) == 1
    assert sum(r.evidence_reused_count or 0 for r in parent) == 1
    assert sum(r.provider_item_count for r in reuse + parent) == 0
    assert sum(r.http_request_count for r in reuse + parent) == 0
    assert sum(r.evidence_created_count or 0 for r in acquisition) == 2
    assert sum(r.evidence_partial_count or 0 for r in acquisition) == 1
    assert sum(r.evidence_missing_count or 0 for r in acquisition) == 1
    assert all(r.actual_cost is None and r.estimated_cost is None and r.currency is None for r in acquisition + reuse + parent)
    db.close()
