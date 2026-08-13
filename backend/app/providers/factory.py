from app.core.config import get_settings
from app.providers.mock import MockSearchVolumeProvider, MockSerpProvider, MockAuthorityProvider
from app.providers.dataforseo import DataForSEOKeywordProvider, DataForSEOSerpProvider, DataForSEOSandboxSerpProvider
from app.providers.runtime_config import DataForSEOConfig, ProviderMode
from app.providers.moz import MozAuthorizedProvider
from app.providers.ahrefs import AhrefsDomainRatingProvider
from app.providers.dataforseo_backlinks import DataForSEOBacklinkSummaryProvider
from app.providers.keyword_metrics import (GoogleAdsKeywordMetricsProvider,
    ImportedKeywordMetricsProvider, MockKeywordMetricsProvider)


def keyword_metrics_provider(*, imported_records=None, provider_name=None):
    """Select the keyword-metrics provider explicitly; never silently fallback."""
    s = get_settings()
    name = (provider_name or s.keyword_metrics_provider or "").strip().lower()
    if name == "mock":
        return MockKeywordMetricsProvider()
    if name == "imported":
        return ImportedKeywordMetricsProvider(imported_records or {})
    if name == "google_ads":
        return GoogleAdsKeywordMetricsProvider(
            enabled=s.google_ads_enabled, live_approved=s.google_ads_live_approved,
            credentials_configured=all((s.google_ads_developer_token, s.google_ads_client_id,
                s.google_ads_client_secret, s.google_ads_refresh_token,
                s.google_ads_customer_id, s.google_ads_login_customer_id)),
            developer_token=s.google_ads_developer_token, client_id=s.google_ads_client_id,
            client_secret=s.google_ads_client_secret, refresh_token=s.google_ads_refresh_token,
            customer_id=s.google_ads_customer_id, login_customer_id=s.google_ads_login_customer_id,
            provider_currency_code=s.google_ads_currency_code,
        )
    if name == "dataforseo":
        return DataForSEOKeywordProvider(s.dataforseo_login or "", s.dataforseo_password or "")
    raise ValueError(f"Unknown keyword metrics provider: {name!r}")


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
    return AhrefsDomainRatingProvider(s.ahrefs_api_key or "", s.ahrefs_api_base_url, s.ahrefs_domain_rating_path, s.ahrefs_proxy_enabled, s.ahrefs_live_approved)


def dataforseo_backlink_proxy_provider():
    s = get_settings()
    return DataForSEOBacklinkSummaryProvider(s.dataforseo_login or "", s.dataforseo_password or "", s.dataforseo_backlink_proxy_enabled, s.dataforseo_backlink_live_approved, s.dataforseo_backlink_estimated_cost, s.dataforseo_backlink_batch_size, s.dataforseo_backlink_budget)
