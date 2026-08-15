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
    dataforseo_backlink_budget: float = 0.0
    dataforseo_backlink_batch_size: int = 1000
    census_api_key: str | None = None
    census_api_enabled: bool = False
    census_api_base_url: str = "https://api.census.gov"
    keyword_metrics_provider: str = "imported"
    google_ads_enabled: bool = False
    google_ads_live_approved: bool = False
    google_ads_production_enabled: bool = False
    google_ads_verified_access_level: str = "UNKNOWN"
    google_ads_developer_token: str | None = None
    google_ads_customer_id: str | None = None
    google_ads_login_customer_id: str | None = None
    google_ads_client_id: str | None = None
    google_ads_client_secret: str | None = None
    google_ads_refresh_token: str | None = None
    # Optional operator override only.  There is deliberately no USD default:
    # Google geo targeting and customer monetary currency are independent.
    google_ads_currency_code: str | None = None
    keyword_metrics_max_batch_size: int = 10_000
    keyword_metrics_requests_per_second: float = 1.0
    keyword_metrics_rate_limit_enabled: bool = False
    google_ads_daily_operation_budget: int | None = None
    auth_secret: str | None = None
    auth_access_token_lifetime_seconds: int = 900
    auth_refresh_token_lifetime_seconds: int = 2_592_000
    keyword_metrics_budget: float | None = None
    keyword_metrics_freshness_days: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
