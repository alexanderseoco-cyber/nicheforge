from app.core.config import get_settings
from app.providers.mock import MockSearchVolumeProvider, MockSerpProvider, MockAuthorityProvider
from app.providers.dataforseo import DataForSEOKeywordProvider, DataForSEOSerpProvider
from app.providers.moz import MozAuthorizedProvider


def search_volume_provider():
    s = get_settings()
    if s.nicheforge_sv_provider == "dataforseo":
        return DataForSEOKeywordProvider(s.dataforseo_login or "", s.dataforseo_password or "")
    return MockSearchVolumeProvider()


def serp_provider():
    s = get_settings()
    if s.nicheforge_serp_provider == "dataforseo":
        return DataForSEOSerpProvider(s.dataforseo_login or "", s.dataforseo_password or "")
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
