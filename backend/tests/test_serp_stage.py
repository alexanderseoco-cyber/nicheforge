import asyncio

from app.providers.contracts import OrganicResult, SerpRequest, SerpResult
from app.services.serp_stage import build_serp_request, request_serp_and_classify


class StubSerpProvider:
    def __init__(self, result):
        self.result = result

    async def fetch(self, requests):
        self.request = requests[0]
        return [self.result]


def _result(count, raw=None):
    return SerpResult(
        keyword="term",
        organic=[OrganicResult(i, f"title-{i}", f"https://example{i}.com") for i in range(1, count + 1)],
        provider="mock",
        raw=raw,
    )


def test_serp_stage_preserves_us_location_code_and_depth():
    request = build_serp_request("term", "United States", "en", 3, "US", 2840)
    provider = StubSerpProvider(_result(3))
    outcome = asyncio.run(request_serp_and_classify(provider, request))
    assert provider.request == request
    assert request.location_code == 2840
    assert outcome.status == "READY"
    assert outcome.reason_code is None


def test_serp_stage_classifies_provider_request_error():
    request = build_serp_request("term", "Albany, NY", "en", 10, "US", 1023191)
    outcome = asyncio.run(request_serp_and_classify(
        StubSerpProvider(_result(10, {"response": {"status_code": 40501, "status_message": "bad request"}})),
        request,
    ))
    assert outcome.status == "ERROR_RETRYABLE"
    assert outcome.reason_code == "SERP_PROVIDER_REQUEST_ERROR"
    assert outcome.provider_status_code == 40501


def test_serp_stage_classifies_insufficient_success_response():
    request = build_serp_request("term", "Worldwide", "en", 10, "WORLDWIDE")
    outcome = asyncio.run(request_serp_and_classify(StubSerpProvider(_result(2)), request))
    assert outcome.status == "ERROR_RETRYABLE"
    assert outcome.reason_code == "SERP_INSUFFICIENT_ORGANIC_RESULTS"
    assert len(outcome.result.organic) == 2
