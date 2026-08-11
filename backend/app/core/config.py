from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    nicheforge_env: str = "development"
    nicheforge_database_url: str = "sqlite:///./nicheforge.db"
    nicheforge_sv_provider: str = "mock"
    nicheforge_serp_provider: str = "mock"
    nicheforge_authority_provider: str = "mock"

    dataforseo_login: str | None = None
    dataforseo_password: str | None = None
    dataforseo_mode: str = "SANDBOX"
    dataforseo_provider_enabled: bool = True
    dataforseo_trial_approved: bool = False
    dataforseo_trial_budget: float = 0.0
    dataforseo_serp_estimated_cost: float = 0.0

    moz_api_base_url: str | None = None
    moz_api_token: str | None = None
    moz_api_auth_mode: str = "bearer"
    moz_url_metrics_path: str | None = None

    ahrefs_api_key: str | None = None
    ahrefs_api_base_url: str = "https://api.ahrefs.com"
    ahrefs_domain_rating_path: str = "/v3/public/domain-rating-free"
    ahrefs_proxy_enabled: bool = False
    ahrefs_live_approved: bool = False
    dataforseo_backlink_proxy_enabled: bool = False
    dataforseo_backlink_live_approved: bool = False
    dataforseo_backlink_estimated_cost: float = 0.0
    dataforseo_backlink_batch_size: int = 1000


@lru_cache
def get_settings() -> Settings:
    return Settings()
