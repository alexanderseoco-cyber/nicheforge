from datetime import datetime, timedelta
from app.models.entities import KeywordMetricEvidence
from app.services.keyword_metrics_workspace import KeywordMetricsFilter, export_rows, filter_and_sort_evidence, stale_evidence_ids


def _item(keyword, volume, provider="mock", status="MAPPED", fresh=True):
    return KeywordMetricEvidence(id=keyword, query_id="q", submitted_keyword=keyword, provider_keyword=keyword, normalized_keyword=keyword, provider=provider, source_kind=provider, avg_monthly_searches=volume, mapping_status=status, fetched_at=datetime.utcnow(), fresh_until=datetime.utcnow()+timedelta(days=1 if fresh else -1))


def test_research_filter_sort_has_no_validation_threshold():
    items = [_item("low", 10), _item("high", 100)]
    result = filter_and_sort_evidence(items, KeywordMetricsFilter())
    assert [x.submitted_keyword for x in result] == ["high", "low"]
    assert len(filter_and_sort_evidence(items, KeywordMetricsFilter(min_search_volume=50))) == 1


def test_stale_history_and_export_are_explicit():
    items = [_item("old", 10, fresh=False), _item("new", 20)]
    assert stale_evidence_ids(items) == ["old"]
    rows = export_rows(items)
    assert rows[0]["keyword"] == "old" and rows[0]["search_volume"] == 10
