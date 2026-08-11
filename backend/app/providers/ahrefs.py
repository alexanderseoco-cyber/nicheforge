from __future__ import annotations

import httpx

from app.providers.contracts import AuthorityTarget, ProxyAuthorityResult


class AhrefsDomainRatingProvider:
    """Ahrefs public Domain Rating endpoint.

    The endpoint is intentionally separate from the Moz AuthorityProvider. DR is
    backlink-strength proxy evidence and must never be normalized as Moz DA.
    """

    provider = "ahrefs"
    metric = "domain_rating"
    operation = "domain_rating_free"

    def __init__(self, api_key: str, base_url: str = "https://api.ahrefs.com", path: str = "/v3/public/domain-rating-free", enabled: bool = False, live_approved: bool = False):
        if not api_key:
            raise ValueError("Ahrefs API key is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.path = path
        self.enabled = enabled
        self.live_approved = live_approved

    def validate_live_execution(self) -> None:
        if not self.enabled:
            raise RuntimeError("AHREFS_PROXY_ENABLED must be true before Ahrefs network execution")
        if not self.live_approved:
            raise RuntimeError("AHREFS_LIVE_APPROVED must be true before Ahrefs network execution")

    async def fetch(self, targets: list[AuthorityTarget]) -> list[ProxyAuthorityResult]:
        self.validate_live_execution()
        results: list[ProxyAuthorityResult] = []
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=30) as client:
            for target in targets:
                response = await client.get(self.base_url + self.path, headers=headers, params={"target": target.root_domain})
                response.raise_for_status()
                payload = response.json()
                metric = (payload.get("domain_rating") or {}).get("domain_rating")
                results.append(ProxyAuthorityResult(target.url, target.root_domain, metric, self.provider, self.metric, payload))
        return results
