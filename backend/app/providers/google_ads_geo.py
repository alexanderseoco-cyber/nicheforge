"""Guarded, structured Google Ads geo-target resolution."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from app.providers.keyword_metrics_safety import KeywordMetricsGuardError

US_STATE_CODES = {
    "AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California","CO":"Colorado","CT":"Connecticut","DE":"Delaware","FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho","IL":"Illinois","IN":"Indiana","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana","ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan","MN":"Minnesota","MS":"Mississippi","MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada","NH":"New Hampshire","NJ":"New Jersey","NM":"New Mexico","NY":"New York","NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma","OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota","TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia","WA":"Washington","WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming","DC":"District of Columbia"
}
US_STATE_NAMES = {name.casefold(): code for code, name in US_STATE_CODES.items()}

def normalize_us_state(value: str | None) -> str:
    value = (value or "").strip()
    if len(value) == 2 and value.upper() in US_STATE_CODES:
        return value.upper()
    return US_STATE_NAMES.get(value.casefold(), "")


class GeoResolutionError(ValueError):
    def __init__(self, message: str, diagnostic: dict | None = None):
        super().__init__(message)
        self.diagnostic = diagnostic or {}


class GeoTransportError(RuntimeError):
    """Sanitized transport failure retaining a stable non-secret category."""
    def __init__(self, category: str, cause: BaseException | None = None):
        self.category = category
        super().__init__(f"Google geo transport failure: {category}")
        if cause is not None:
            self.__cause__ = cause


def classify_transport_exception(exc: BaseException) -> str:
    text = str(exc).casefold()
    name = type(exc).__name__.casefold()
    if any(x in text for x in ("credential", "refresh", "oauth", "unauth")): return "credential_refresh"
    if any(x in text for x in ("tls", "ssl", "certificate")): return "tls"
    if any(x in text for x in ("dns", "name or service", "resolve")): return "dns_network"
    if any(x in text for x in ("unavailable", "channel", "grpc")): return "grpc_unavailable"
    if any(x in text for x in ("serialize", "request", "invalid")): return "request_contract"
    if "transport" in name or "transport" in text: return "transport"
    return "client_or_endpoint"


@dataclass(frozen=True)
class GoogleGeoTarget:
    city: str
    state: str
    country_code: str
    criterion_id: str
    resource_name: str
    provider_name: str
    target_type: str
    status: str | None
    mapping_status: str
    retrieved_at: datetime


class GoogleAdsGeoTargetResolver:
    def __init__(self, *, client_factory=None, enabled=False, live_approved=False,
                 credentials_configured=False, cache=None, freshness_days=30):
        self.client_factory = client_factory
        self.enabled = enabled
        self.live_approved = live_approved
        self.credentials_configured = credentials_configured
        self.cache = cache if cache is not None else {}
        self.freshness = timedelta(days=freshness_days)
        self.network_calls = 0
        self.network_attempts = 0
        self.network_successes = 0
        self.network_failures = 0

    async def resolve(self, city: str, state: str, country_code: str = "US", locale: str = "en") -> GoogleGeoTarget:
        key = (city.casefold().strip(), state.casefold().strip(), country_code.upper())
        cached = self.cache.get(key)
        if cached and datetime.now(timezone.utc) - cached.retrieved_at <= self.freshness:
            return cached
        if not self.enabled:
            raise KeywordMetricsGuardError("Google Ads geo provider is disabled")
        if not self.live_approved:
            raise KeywordMetricsGuardError("Google Ads geo resolution requires explicit approval")
        if not self.credentials_configured:
            raise KeywordMetricsGuardError("Google Ads geo credentials are not configured")
        try:
            client = self.client_factory()
            service = client.get_service("GeoTargetConstantService")
            request = client.get_type("SuggestGeoTargetConstantsRequest")
            request.locale = locale
            request.country_code = country_code.upper()
            request.location_names.names.append(city)
            self.network_attempts += 1
            try:
                response = service.suggest_geo_target_constants(request=request)
                self.network_calls += 1
                self.network_successes += 1
            except Exception:
                self.network_failures += 1
                raise
        except (GeoResolutionError, KeywordMetricsGuardError):
            raise
        except Exception as exc:
            raise GeoTransportError(classify_transport_exception(exc), exc) from exc
        candidates = []
        rejected = []
        for suggestion in getattr(response, "geo_target_constant_suggestions", []):
            target = getattr(suggestion, "geo_target_constant", suggestion)
            name = str(getattr(target, "name", ""))
            target_country = str(getattr(target, "country_code", "")).upper()
            target_type = str(getattr(target, "target_type", ""))
            canonical = str(getattr(target, "canonical_name", ""))
            canonical_parts = [part.strip() for part in canonical.split(",")]
            provider_state = canonical_parts[1] if len(canonical_parts) >= 2 else ""
            if name.casefold() == city.casefold() and target_country == country_code.upper() and normalize_us_state(state) and normalize_us_state(provider_state) == normalize_us_state(state) and "CITY" in target_type.upper():
                resource = str(getattr(target, "resource_name", ""))
                criterion_id = resource.rsplit("/", 1)[-1]
                candidates.append(GoogleGeoTarget(city, state, country_code.upper(), criterion_id, resource, name, target_type, str(getattr(target, "status", "")) or None, "MAPPED", datetime.now(timezone.utc)))
            else:
                rejected.append({"name": name, "canonical_name": canonical, "country_code": target_country, "target_type": target_type})
        diagnostic = {"suggestion_count": len(getattr(response, "geo_target_constant_suggestions", [])), "candidate_count": len(candidates), "rejected_candidates": rejected[:20]}
        if not candidates:
            raise GeoResolutionError("NOT_FOUND", diagnostic)
        if len(candidates) > 1:
            diagnostic["candidate_count"] = len(candidates)
            raise GeoResolutionError("AMBIGUOUS_GEO_TARGET", diagnostic)
        self.cache[key] = candidates[0]
        return candidates[0]
