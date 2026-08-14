import pytest

from app.providers.contracts import KeywordMetricRequest, KeywordMetricResult
from app.services.keyword_metrics_batch import CachedMetric, KeywordMetricsBatchOrchestrator


class CountingProvider:
    def __init__(self, results): self.results, self.calls = results, 0
    async def fetch(self, requests): self.calls += 1; return self.results


@pytest.mark.asyncio
async def test_fresh_cache_hits_never_call_provider():
    request = KeywordMetricRequest("term", "City", "en")
    provider = CountingProvider([])
    cached = CachedMetric(KeywordMetricResult("term", 10, provider="imported"), fresh=True)
    result = await KeywordMetricsBatchOrchestrator(provider, {KeywordMetricsBatchOrchestrator._key(request): cached}).execute([request])
    assert provider.calls == 0 and result.cache_hits == 1


@pytest.mark.asyncio
async def test_only_stale_and_missing_items_are_batched():
    fresh = KeywordMetricRequest("fresh", "City", "en"); stale = KeywordMetricRequest("stale", "City", "en"); missing = KeywordMetricRequest("missing", "City", "en")
    provider = CountingProvider([KeywordMetricResult("stale", 2), KeywordMetricResult("missing", 3)])
    cache = {KeywordMetricsBatchOrchestrator._key(fresh): CachedMetric(KeywordMetricResult("fresh", 1), True), KeywordMetricsBatchOrchestrator._key(stale): CachedMetric(KeywordMetricResult("stale", 1), False)}
    result = await KeywordMetricsBatchOrchestrator(provider, cache).execute([fresh, stale, missing])
    assert provider.calls == 1 and result.cache_hits == 1 and result.results["fresh"].avg_monthly_searches == 1


@pytest.mark.asyncio
async def test_partial_response_is_explicitly_unmapped():
    requests = [KeywordMetricRequest("one"), KeywordMetricRequest("two")]
    provider = CountingProvider([KeywordMetricResult("one", 1)])
    result = await KeywordMetricsBatchOrchestrator(provider).execute(requests)
    assert result.mapping_status["one"] == "MAPPED" and result.mapping_status["two"] == "UNMAPPED"
    assert result.unmapped_count == 1


@pytest.mark.asyncio
async def test_resume_does_not_duplicate_provider_call_or_evidence():
    request = KeywordMetricRequest("term")
    provider = CountingProvider([KeywordMetricResult("term", 7)])
    orchestrator = KeywordMetricsBatchOrchestrator(provider)
    first = await orchestrator.execute([request]); second = await orchestrator.execute([request])
    assert first.provider_requests == 1 and second.provider_requests == 0
    assert provider.calls == 1 and second.mapping_status["term"] == "RESUMED"
def test_batch_cache_identity_includes_country_and_provider_geo_target():
    us = KeywordMetricRequest("term", country_code="US", location_target={"country_code": "US"})
    pk = KeywordMetricRequest("term", country_code="PK", location_target={"country_code": "PK"})
    assert KeywordMetricsBatchOrchestrator._key(us) != KeywordMetricsBatchOrchestrator._key(pk)
