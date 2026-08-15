from pydantic import BaseModel, Field, ConfigDict


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
    kd_enabled: bool = True
    kd_provider: str = "moz"
    kd_threshold: float = 15.0
    kd_operator: str = "<"
    kd_mode: str = "PRIORITY"


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    profile: ValidationProfile = Field(default_factory=ValidationProfile)


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
