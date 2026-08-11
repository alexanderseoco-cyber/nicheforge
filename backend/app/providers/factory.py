from app.core.config import get_settings
from app.providers.mock import MockSearchVolumeProvider, MockSerpProvider, MockAuthorityProvider
from app.providers.dataforseo import DataForSEOKeywordProvider, DataForSEOSerpProvider, DataForSEOSandboxSerpProvider
from app.providers.runtime_config import DataForSEOConfig, ProviderMode
from app.providers.moz import MozAuthorizedProvider
from app.providers.ahrefs import AhrefsDomainRatingProvider


def search_volume_provider():
    s = get_settings()
    if s.nicheforge_sv_provider == "dataforseo":
        return DataForSEOKeywordProvider(s.dataforseo_login or "", s.dataforseo_password or "")
    return MockSearchVolumeProvider()


def serp_provider():
    s = get_settings()
    if s.nicheforge_serp_provider == "dataforseo":
        config = DataForSEOConfig.from_settings(s)
        config.validate_paid_execution(config.standard_serp_cost, s.dataforseo_trial_approved)
        if config.mode == ProviderMode.SANDBOX:
            return DataForSEOSandboxSerpProvider()
        return DataForSEOSerpProvider(s.dataforseo_login or "", s.dataforseo_password or "", mode=config.mode)
    return MockSerpProvider()


def authority_provider():
    s = get_settings()
    if s.nicheforge_authority_provider == "moz":
        return MozAuthorizedProvider(
            s.moz_api_base_url or "",
            s.moz_url_metrics_path or "",
            s.moz_api_token or "",
            s.moz_api_auth_mode,
        )
    return MockAuthorityProvider()


def ahrefs_proxy_provider():
    s = get_settings()
    return AhrefsDomainRatingProvider(s.ahrefs_api_key or "", s.ahrefs_api_base_url, s.ahrefs_domain_rating_path)
