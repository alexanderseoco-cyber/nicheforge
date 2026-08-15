from __future__ import annotations

from dataclasses import dataclass
import re


class KeywordMetricsGuardError(RuntimeError, PermissionError):
    """Safe pre-transport guard failure, compatible with runtime callers."""


@dataclass(frozen=True)
class KeywordMetricsSafetyConfig:
    provider: str
    enabled: bool = False
    live_approved: bool = False
    credentials_configured: bool = False
    max_batch_size: int = 10_000
    requests_per_second: float = 1.0
    budget: float | None = None
    freshness_days: int = 30
    production_enabled: bool = False
    verified_access_level: str = "UNKNOWN"

    def validate(self, requested_items: int = 0, estimated_cost: float | None = 0.0) -> None:
        if self.provider not in {"mock", "imported", "google_ads", "dataforseo"}:
            raise ValueError(f"Unknown keyword metrics provider: {self.provider!r}")
        if requested_items < 0 or requested_items > self.max_batch_size:
            raise ValueError("Keyword metrics batch exceeds configured provider batch limit")
        if self.provider in {"google_ads", "dataforseo"}:
            if not self.enabled:
                raise KeywordMetricsGuardError("Keyword metrics provider is disabled")
            if not self.live_approved:
                raise KeywordMetricsGuardError("Keyword metrics live execution requires explicit approval")
            if not self.credentials_configured:
                raise KeywordMetricsGuardError("Keyword metrics provider credentials are not configured")
        if self.provider == "google_ads" and self.production_enabled:
            access_level = self.verified_access_level.upper()
            if access_level not in {"BASIC", "STANDARD"}:
                raise KeywordMetricsGuardError(
                    "Google Ads production execution requires explicitly verified BASIC or STANDARD access"
                )
        if self.budget is not None and estimated_cost is not None and estimated_cost > self.budget:
            raise ValueError("Estimated keyword metrics cost exceeds configured budget")
        if self.requests_per_second <= 0:
            raise ValueError("Keyword metrics request rate must be positive")
        if self.freshness_days < 0:
            raise ValueError("Keyword metrics freshness must not be negative")


def redact_secret_text(value: object, secrets: list[str | None]) -> str:
    text = str(value)
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    text = re.sub(r"(token|secret|password|key)=([^\s,;]+)", r"\1=[REDACTED]", text, flags=re.I)
    return text
