"""Internal SERP request and response-classification boundary."""

from dataclasses import dataclass
from typing import Any

from app.providers.contracts import SerpRequest, SerpResult, SerpProvider
from app.services.serp_coverage import SerpCoverage, classify_serp_coverage


@dataclass(frozen=True)
class SerpStageResult:
    result: SerpResult | None
    status: str
    reason_code: str | None
    request: SerpRequest
    provider_status_code: int | None = None
    provider_status_message: str | None = None
    coverage: SerpCoverage | None = None


def build_serp_request(
    keyword: str,
    location_name: str,
    language_code: str,
    depth: int,
    country_code: str,
    location_code: int | None = None,
) -> SerpRequest:
    """Build the existing provider request without broadening target semantics."""
    return SerpRequest(keyword, location_name, language_code, depth, country_code, location_code)


def _provider_status(raw: Any) -> tuple[int | None, str | None]:
    response = (raw or {}).get("response", {}) if isinstance(raw, dict) else {}
    return response.get("status_code"), response.get("status_message")


async def request_serp_and_classify(provider: SerpProvider, request: SerpRequest, *, minimum_organic_rows: int | None = None, minimum_organic_coverage: float | None = None) -> SerpStageResult:
    """Execute one existing SERP request and preserve current error semantics."""
    result = (await provider.fetch([request]))[0]
    status_code, status_message = _provider_status(result.raw)
    if status_code not in (None, 20000):
        coverage = classify_serp_coverage(requested_depth=request.depth, usable_organic_count=len(result.organic), minimum_organic_rows=minimum_organic_rows, minimum_organic_coverage=minimum_organic_coverage, provider_success=False)
        return SerpStageResult(
            result=result,
            status="ERROR_RETRYABLE",
            reason_code="SERP_PROVIDER_REQUEST_ERROR",
            request=request,
            provider_status_code=status_code,
            provider_status_message=status_message,
            coverage=coverage,
        )
    coverage = classify_serp_coverage(requested_depth=request.depth, usable_organic_count=len(result.organic), minimum_organic_rows=minimum_organic_rows, minimum_organic_coverage=minimum_organic_coverage)
    if not coverage.sufficient_for_downstream:
        return SerpStageResult(
            result=result,
            # Preserve the existing executor-facing retry status for the
            # insufficient case; the authoritative semantic state is carried
            # by ``coverage.evidence_state``.
            status="ERROR_RETRYABLE",
            reason_code="SERP_INSUFFICIENT_ORGANIC_RESULTS",
            request=request,
            coverage=coverage,
        )
    return SerpStageResult(result=result, status="READY", reason_code=None, request=request, coverage=coverage)
