from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, Any


@dataclass
class KeywordMetricRequest:
    keyword: str
    location_name: str | None = None
    language_code: str = "en"


@dataclass
class KeywordMetricResult:
    keyword: str
    avg_monthly_searches: int | None
    cpc: float | None = None
    competition: float | None = None
    keyword_difficulty: float | None = None
    monthly_history: list[dict] = field(default_factory=list)
    provider: str = "unknown"
    raw: Any = None


@dataclass
class OrganicResult:
    position: int
    title: str | None
    url: str


@dataclass
class SerpRequest:
    keyword: str
    location_name: str
    language_code: str = "en"
    depth: int = 10


@dataclass
class SerpResult:
    keyword: str
    organic: list[OrganicResult]
    provider: str
    raw: Any = None


@dataclass
class AuthorityTarget:
    url: str
    root_domain: str


@dataclass
class AuthorityResult:
    url: str
    root_domain: str
    da: float | None
    pa: float | None = None
    spam_score: float | None = None
    linking_root_domains: int | None = None
    backlinks: int | None = None
    provider: str = "unknown"
    raw: Any = None


class SearchVolumeProvider(Protocol):
    async def fetch(self, requests: list[KeywordMetricRequest]) -> list[KeywordMetricResult]: ...


class SerpProvider(Protocol):
    async def fetch(self, requests: list[SerpRequest]) -> list[SerpResult]: ...


class AuthorityProvider(Protocol):
    async def fetch(self, targets: list[AuthorityTarget]) -> list[AuthorityResult]: ...


@dataclass
class ProxyAuthorityResult:
    url: str
    root_domain: str
    domain_rating: float | None
    provider: str = "ahrefs"
    metric: str = "domain_rating"
    raw: Any = None


@dataclass
class BacklinkFeatureResult:
    target: str
    rank: int | None = None
    backlinks: int | None = None
    referring_domains: int | None = None
    referring_main_domains: int | None = None
    referring_ips: int | None = None
    referring_subnets: int | None = None
    referring_domains_nofollow: int | None = None
    referring_main_domains_nofollow: int | None = None
    backlinks_spam_score: float | None = None
    provider: str = "dataforseo"
    metric: str = "backlink_summary"
    raw: Any = None
    actual_cost: float | None = None
    api_status_code: int | None = None
    api_status_message: str | None = None
