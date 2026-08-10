from __future__ import annotations
import base64
import os
import httpx
from app.providers.contracts import (
    KeywordMetricRequest, KeywordMetricResult, SerpRequest, SerpResult, OrganicResult
)


class DataForSEOClient:
    def __init__(self, login: str, password: str, base_url: str = "https://api.dataforseo.com"):
        token = base64.b64encode(f"{login}:{password}".encode()).decode()
        self.headers = {"Authorization": f"Basic {token}", "Content-Type": "application/json"}
        self.base_url = base_url.rstrip("/")

    async def post(self, path: str, payload: list[dict]) -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(self.base_url + path, headers=self.headers, json=payload)
            r.raise_for_status()
            return r.json()


class DataForSEOKeywordProvider:
    """Live historical search-volume adapter.

    Endpoint is based on DataForSEO Labs historical search volume. Keep parsing here;
    the rest of NicheForge only sees normalized KeywordMetricResult objects.
    """

    def __init__(self, login: str, password: str):
        self.client = DataForSEOClient(login, password)

    async def fetch(self, requests: list[KeywordMetricRequest]) -> list[KeywordMetricResult]:
        if not requests:
            return []
        # Grouping by location is intentionally simple for MVP. Production should batch same-location requests.
        results: list[KeywordMetricResult] = []
        for req in requests:
            payload = [{
                "keywords": [req.keyword],
                "location_name": req.location_name or "United States",
                "language_code": req.language_code,
            }]
            data = await self.client.post("/v3/dataforseo_labs/google/historical_search_volume/live", payload)
            item = (((data.get("tasks") or [{}])[0].get("result") or [{}])[0].get("items") or [{}])[0]
            info = item.get("keyword_info") or {}
            results.append(KeywordMetricResult(
                keyword=req.keyword,
                avg_monthly_searches=info.get("search_volume"),
                cpc=info.get("cpc"),
                competition=info.get("competition"),
                monthly_history=info.get("monthly_searches") or [],
                provider="dataforseo",
                raw=item,
            ))
        return results


class DataForSEOSerpProvider:
    def __init__(self, login: str, password: str):
        self.client = DataForSEOClient(login, password)

    async def fetch(self, requests: list[SerpRequest]) -> list[SerpResult]:
        out: list[SerpResult] = []
        for req in requests:
            payload = [{
                "keyword": req.keyword,
                "location_name": req.location_name,
                "language_code": req.language_code,
                "depth": req.depth,
            }]
            data = await self.client.post("/v3/serp/google/organic/live/regular", payload)
            task = (data.get("tasks") or [{}])[0]
            result = (task.get("result") or [{}])[0]
            organic: list[OrganicResult] = []
            for item in result.get("items") or []:
                if item.get("type") != "organic":
                    continue
                organic.append(OrganicResult(
                    position=int(item.get("rank_absolute") or item.get("rank_group") or len(organic)+1),
                    title=item.get("title"),
                    url=item.get("url"),
                ))
                if len(organic) >= req.depth:
                    break
            out.append(SerpResult(req.keyword, organic, "dataforseo", raw=result))
        return out


class DataForSEOSandboxSerpProvider:
    """Deterministic Sandbox response mapper.

    Network transport is deliberately injected by callers. This keeps normal
    tests offline and prevents Sandbox from silently becoming a paid adapter.
    """
    provider = "dataforseo_sandbox"
    mode = "SANDBOX"

    def __init__(self, transport=None):
        self.transport = transport or self._default_transport

    async def _default_transport(self, request: SerpRequest) -> dict:
        """Opt-in, zero-cost Sandbox live SERP request."""
        from app.core.config import get_settings
        settings = get_settings()
        if not settings.dataforseo_login or not settings.dataforseo_password:
            raise RuntimeError("DataForSEO Sandbox credentials are not configured")
        client = DataForSEOClient(
            settings.dataforseo_login,
            settings.dataforseo_password,
            base_url="https://sandbox.dataforseo.com",
        )
        return await client.post("/v3/serp/google/organic/live/regular", [{
            "keyword": request.keyword,
            "location_name": request.location_name,
            "language_code": request.language_code,
            "depth": request.depth,
        }])

    @staticmethod
    def map_response(req: SerpRequest, data: dict) -> SerpResult:
        task = (data.get("tasks") or [{}])[0]
        result = (task.get("result") or [{}])[0]
        organic = []
        for item in result.get("items") or []:
            if item.get("type") != "organic" or not item.get("url"):
                continue
            organic.append(OrganicResult(
                position=int(item.get("rank_absolute") or item.get("rank_group") or len(organic) + 1),
                title=item.get("title"), url=item["url"],
            ))
            if len(organic) >= req.depth:
                break
        return SerpResult(req.keyword, organic, DataForSEOSandboxSerpProvider.provider,
                          raw={"mode": "SANDBOX", "response": result})

    async def fetch(self, requests: list[SerpRequest]) -> list[SerpResult]:
        if os.getenv("NICHEFORGE_ENABLE_DATAFORSEO_SANDBOX_SMOKE") != "1":
            raise RuntimeError("Sandbox smoke transport is disabled")
        if self.transport is None:
            raise RuntimeError("Sandbox transport is not configured")
        results = []
        for request in requests:
            try:
                results.append(self.map_response(request, await self.transport(request)))
            except httpx.HTTPStatusError as exc:
                body_status = "unavailable"
                body_message = "unavailable"
                try:
                    payload = exc.response.json()
                    body_status = str(payload.get("status_code", "unavailable"))
                    body_message = str(payload.get("status_message", "unavailable"))
                except (ValueError, TypeError):
                    pass
                raise RuntimeError(
                    "DATAFORSEO_SANDBOX_NETWORK_FAILURE: "
                    f"category=http_http_status; exception_type={type(exc).__name__}; "
                    f"exception_message={exc.response.status_code} {exc.response.reason_phrase}; "
                    f"http_status={exc.response.status_code}; response_received=true; "
                    f"json_parsed={body_status != 'unavailable'}; "
                    f"api_status_code={body_status}; api_status_message={body_message}; "
                    "canonical_mapping_reached=false; credentials_exposed=false"
                ) from exc
            except httpx.TimeoutException as exc:
                raise RuntimeError(
                    "DATAFORSEO_SANDBOX_NETWORK_FAILURE: "
                    f"category=timeout; exception_type={type(exc).__name__}; "
                    f"exception_message={type(exc).__name__}; response_received=false; "
                    "json_parsed=false; canonical_mapping_reached=false; credentials_exposed=false"
                ) from exc
            except httpx.ConnectError as exc:
                raise RuntimeError(
                    "DATAFORSEO_SANDBOX_NETWORK_FAILURE: "
                    f"category=network; exception_type={type(exc).__name__}; "
                    f"exception_message={type(exc).__name__}; response_received=false; "
                    "json_parsed=false; canonical_mapping_reached=false; credentials_exposed=false"
                ) from exc
            except Exception as exc:
                raise RuntimeError(
                    "DATAFORSEO_SANDBOX_NETWORK_FAILURE: "
                    f"category=local_or_response; exception_type={type(exc).__name__}; "
                    f"exception_message={type(exc).__name__}; response_received=unknown; "
                    "json_parsed=unknown; canonical_mapping_reached=unknown; credentials_exposed=false"
                ) from exc
        return results
