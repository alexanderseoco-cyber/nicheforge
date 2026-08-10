from __future__ import annotations
import httpx
from app.providers.contracts import AuthorityTarget, AuthorityResult


class MozAuthorizedProvider:
    """Authorized Moz adapter with configurable endpoint and auth.

    We intentionally do not hardcode a Moz HTTP path/response mapping that has not
    been verified for the user's account. Configure MOZ_API_BASE_URL,
    MOZ_URL_METRICS_PATH and MOZ_API_TOKEN from current Moz documentation/account.

    Expected normalized fields are mapped in `_normalize_item`. Update only this
    adapter when Moz's contract differs; never change validation business logic.
    """

    def __init__(self, base_url: str, path: str, token: str, auth_mode: str = "bearer"):
        if not base_url or not path or not token:
            raise ValueError("Moz API configuration is incomplete")
        self.base_url = base_url.rstrip("/")
        self.path = path
        self.token = token
        self.auth_mode = auth_mode

    def _headers(self) -> dict[str, str]:
        if self.auth_mode == "bearer":
            return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        return {"Authorization": self.token, "Content-Type": "application/json"}

    def _normalize_item(self, target: AuthorityTarget, item: dict) -> AuthorityResult:
        # Field aliases are deliberately permissive. Confirm exact current fields for production.
        return AuthorityResult(
            url=target.url,
            root_domain=target.root_domain,
            da=item.get("domain_authority", item.get("da")),
            pa=item.get("page_authority", item.get("pa")),
            spam_score=item.get("spam_score"),
            linking_root_domains=item.get("linking_root_domains"),
            backlinks=item.get("external_links", item.get("backlinks")),
            provider="moz",
            raw=item,
        )

    async def fetch(self, targets: list[AuthorityTarget]) -> list[AuthorityResult]:
        payload = [{"target": t.url} for t in targets]
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(self.base_url + self.path, headers=self._headers(), json=payload)
            r.raise_for_status()
            data = r.json()
        items = data if isinstance(data, list) else data.get("results") or data.get("items") or []
        if len(items) != len(targets):
            raise RuntimeError("Moz response could not be aligned with requested targets; update adapter mapping")
        return [self._normalize_item(t, item) for t, item in zip(targets, items)]
