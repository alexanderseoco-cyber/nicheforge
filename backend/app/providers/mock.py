import hashlib
from urllib.parse import urlparse
from app.providers.contracts import (
    KeywordMetricRequest, KeywordMetricResult, SerpRequest, SerpResult, OrganicResult,
    AuthorityTarget, AuthorityResult
)


def _n(text: str, mod: int) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest()[:8], 16) % mod


class MockSearchVolumeProvider:
    async def fetch(self, requests: list[KeywordMetricRequest]) -> list[KeywordMetricResult]:
        out = []
        for r in requests:
            # deterministic 0..990 in steps of 10
            sv = _n(r.keyword + (r.location_name or ""), 100) * 10
            out.append(KeywordMetricResult(r.keyword, sv, cpc=round((_n(r.keyword, 5000) / 100), 2), keyword_difficulty=float(_n(r.keyword + "-kd", 30)), provider="mock"))
        return out


class MockSerpProvider:
    async def fetch(self, requests: list[SerpRequest]) -> list[SerpResult]:
        out = []
        for r in requests:
            organic = []
            for i in range(1, min(r.depth, 10) + 1):
                slug = hashlib.md5(f"{r.keyword}-{i}".encode()).hexdigest()[:8]
                organic.append(OrganicResult(i, f"Result {i}", f"https://site-{slug}.example/service"))
            out.append(SerpResult(r.keyword, organic, "mock", raw={"mock": True}))
        return out


class MockAuthorityProvider:
    async def fetch(self, targets: list[AuthorityTarget]) -> list[AuthorityResult]:
        out = []
        for t in targets:
            da = float(_n(t.root_domain, 50))
            pa = float(_n(t.url, 60))
            out.append(AuthorityResult(t.url, t.root_domain, da=da, pa=pa, spam_score=float(_n(t.root_domain+"spam", 30)), provider="mock"))
        return out
