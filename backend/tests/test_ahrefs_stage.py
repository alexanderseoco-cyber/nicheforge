from app.services.ahrefs_stage import ahrefs_stage_not_executed


def test_ahrefs_stage_disabled_is_explicitly_unavailable():
    result = ahrefs_stage_not_executed([])
    assert result.executed is False
    assert result.available is False
    assert result.coverage_count == 0
    assert result.requested_count == 0
