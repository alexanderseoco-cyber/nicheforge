from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, model_validator


class ValidationProfile(BaseModel):
    population_enabled: bool = True
    search_volume_enabled: bool = True
    min_population: int = 20_000
    max_population: int = 120_000
    min_search_volume: int | None = 300
    da_threshold: float = 10.0
    required_low_da_count: int = 4
    minimum_weak_domains: int = 4
    ideal_weak_domains: int = 5
    authority_evaluation_mode: str = "ADAPTIVE"
    authority_batch_size: int = 5
    adaptive_seek_ideal: bool = True
    organic_depth: int = 10
    minimum_organic_rows: int | None = None
    minimum_organic_coverage: float = 0.90
    kd_enabled: bool = True
    kd_provider: str = "moz"
    kd_threshold: float = 15.0
    kd_operator: str = "<"
    kd_mode: str = "PRIORITY"

    @model_validator(mode="after")
    def validate_serp_policy(self):
        if self.organic_depth <= 0:
            raise ValueError("organic_depth must be greater than zero")
        if self.minimum_organic_rows is None:
            self.minimum_organic_rows = min(9, self.organic_depth)
        if self.minimum_organic_rows <= 0 or self.minimum_organic_rows > self.organic_depth:
            raise ValueError("minimum_organic_rows must be positive and no greater than organic_depth")
        if not 0 < self.minimum_organic_coverage <= 1.0:
            raise ValueError("minimum_organic_coverage must be greater than zero and at most 1.0")
        return self


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    profile: ValidationProfile = Field(default_factory=ValidationProfile)
    handoff_ids: list[str] = Field(default_factory=list)

class ProjectHandoffAttachRequest(BaseModel):
    handoff_ids: list[str] = Field(min_length=1)
    location_overrides: dict[str, dict] = Field(default_factory=dict)

class ProjectHandoffAttachResponse(BaseModel):
    project_id: str
    created_count: int
    existing_count: int
    project_candidate_ids: list[str]
    results: list[dict] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)


class NicheInput(BaseModel):
    service_term: str
    broad_category: str | None = None
    micro_niche: str | None = None


class CandidateGenerateRequest(BaseModel):
    niches: list[NicheInput]
    profile: ValidationProfile | None = None
    state_codes: list[str] | None = None


class CandidateOut(BaseModel):
    id: str
    keyword: str
    city: str | None
    state: str | None
    population: int | None
    search_volume: int | None
    cpc: float | None
    low_da_count: int | None
    status: str
    automatic_pass: bool | None
    reason_codes: list


class RunRequest(BaseModel):
    candidate_ids: list[str] | None = None
    profile: ValidationProfile | None = None


class RunCreate(BaseModel):
    profile: ValidationProfile | None = None
    candidate_ids: list[str] | None = None


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    status: str
    counters: dict
    min_search_volume: int
    da_threshold: float
    required_low_da_count: int
    minimum_weak_domains: int
    ideal_weak_domains: int
    authority_evaluation_mode: str
    progress: int = 0
    candidate_results: list[dict] = Field(default_factory=list)

class OverlayRequest(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=20)


class KeywordMetricTarget(BaseModel):
    location_name: str | None = None
    location_target: dict = Field(default_factory=dict)
    language_code: str = "en"
    country_code: str = "US"


class KeywordMetricsRequest(BaseModel):
    keywords: list[str] = Field(min_length=1)
    target: KeywordMetricTarget = Field(default_factory=KeywordMetricTarget)
    force_refresh: bool = False
    provider: str = "google_ads"


class KeywordMetricsBatchLocation(BaseModel):
    city: str
    state_code: str
    country_code: str = "US"


class KeywordMetricsBatchRequest(BaseModel):
    keywords: list[str] = Field(min_length=1)
    locations: list[KeywordMetricsBatchLocation] = Field(min_length=1)
    language_code: str = "en"
    country_code: str = "US"
    minimum_sv: int | None = 260
    force_refresh: bool = False
    provider: str = "google_ads"


class KeywordMetricsPreview(BaseModel):
    submitted_count: int
    deduplicated_count: int
    cache_hits: int
    provider_requests: int
    estimated_cost: float | None
    transport_would_occur: bool
    provider: str
    total_combinations: int = 0
    fresh_cache_savings: int = 0
    keywords_requiring_provider_evidence: int = 0
    target_count: int = 1
    language_count: int = 1
    chunk_size: int = 10_000
    planned_rpc_count: int = 0
    operation_budget_status: str = "UNKNOWN_UNVERIFIED"
    provider_capacity_remaining: int | None = None
    effective_executable_allowance: int | None = None


class KeywordMetricResultOut(BaseModel):
    id: str | None = None
    submitted_keyword: str
    provider_keyword: str | None = None
    provider: str
    location_name: str | None = None
    location_target: dict = Field(default_factory=dict)
    language_code: str
    country_code: str
    avg_monthly_searches: int | None = None
    cpc: float | None = None
    competition: float | None = None
    competition_index: int | None = None
    low_bid: float | None = None
    high_bid: float | None = None
    provider_currency_code: str | None = None
    usd_cpc: float | None = None
    usd_low_bid: float | None = None
    usd_high_bid: float | None = None
    fx_rate: float | None = None
    fx_rate_date: str | None = None
    fx_source: str | None = None
    monthly_history: list = Field(default_factory=list)
    fetched_at: str | None = None
    fresh_until: str | None = None
    mapping_status: str
    cost: float | None = None
    commercial_metrics: dict | None = None


class KeywordMetricsResearchResponse(BaseModel):
    batch_id: str
    status: str
    provider: str
    submitted_count: int
    mapped_count: int
    unmapped_count: int
    provider_requests: int
    results: list[KeywordMetricResultOut]


class KeywordMetricsHandoffRequest(BaseModel):
    evidence_ids: list[str] = Field(min_length=1)
    validation_profile: ValidationProfile = Field(default_factory=ValidationProfile)


class KeywordMetricsHandoffResponse(BaseModel):
    handoff_ids: list[str]
    evidence_ids: list[str]
    selected_count: int
    provider_requests: int = 0
    new_count: int = 0
    existing_count: int = 0
    existing_evidence_ids: list[str] = Field(default_factory=list)
    new_handoff_ids: list[str] = Field(default_factory=list)
    existing_handoff_ids: list[str] = Field(default_factory=list)
    all_handoff_ids: list[str] = Field(default_factory=list)

class KeywordMetricsHandoffOut(BaseModel):
    handoff_id: str
    evidence_id: str
    keyword: str
    search_volume: int | None
    country_code: str
    location_target: dict
    language_code: str
    provider: str
    provider_keyword: str | None = None
    validation_profile: dict
    created_at: datetime
    status: str
    validation_scope: str
    scope_reason: str
    location_status: str
    population_applicability: str
    serp_mode: str
    readiness_status: str
