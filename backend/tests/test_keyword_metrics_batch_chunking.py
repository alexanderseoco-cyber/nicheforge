import pytest
from app.providers.contracts import KeywordMetricRequest, KeywordMetricResult
from app.services.keyword_metrics_batch import KeywordMetricsBatchOrchestrator


class ChunkProvider:
    def __init__(self): self.calls=[]
    async def fetch(self, requests):
        self.calls.append(list(requests))
        return [KeywordMetricResult(r.keyword, len(r.keyword), provider="mock", cost=0.01) for r in requests]


@pytest.mark.asyncio
async def test_arbitrary_input_is_chunked_and_accounted():
    provider=ChunkProvider(); requests=[KeywordMetricRequest(f"term-{i}") for i in range(25)]
    result=await KeywordMetricsBatchOrchestrator(provider, chunk_size=10).execute(requests)
    assert [len(x) for x in provider.calls] == [10,10,5]
    assert result.provider_requests == result.chunks == 3
    assert result.actual_cost == 0.25
    assert len(result.results) == 25
