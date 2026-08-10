from pydantic import BaseModel, Field, ConfigDict


class ValidationProfile(BaseModel):
    min_population: int = 20_000
    max_population: int = 120_000
    min_search_volume: int = 300
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
