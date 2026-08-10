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

    moz_api_base_url: str | None = None
    moz_api_token: str | None = None
    moz_api_auth_mode: str = "bearer"
    moz_url_metrics_path: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
