from __future__ import annotations
import base64
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
