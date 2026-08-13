"""Guarded, structured Google Ads geo-target resolution."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from app.providers.keyword_metrics_safety import KeywordMetricsGuardError


class GeoResolutionError(ValueError):
    pass


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
        client = self.client_factory()
        service = client.get_service("GeoTargetConstantService")
        request = client.get_type("SuggestGeoTargetConstantsRequest")
        request.locale = locale
        request.country_code = country_code.upper()
        request.location_names.names.append(city)
        self.network_calls += 1
        response = service.suggest_geo_target_constants(request=request)
        candidates = []
        for suggestion in getattr(response, "geo_target_constant_suggestions", []):
            target = getattr(suggestion, "geo_target_constant", suggestion)
            name = str(getattr(target, "name", ""))
            target_country = str(getattr(target, "country_code", "")).upper()
            target_type = str(getattr(target, "target_type", ""))
            canonical = str(getattr(target, "canonical_name", ""))
            if name.casefold() == city.casefold() and target_country == country_code.upper() and state.casefold() in canonical.casefold() and "CITY" in target_type.upper():
                resource = str(getattr(target, "resource_name", ""))
                criterion_id = resource.rsplit("/", 1)[-1]
                candidates.append(GoogleGeoTarget(city, state, country_code.upper(), criterion_id, resource, name, target_type, str(getattr(target, "status", "")) or None, "MAPPED", datetime.now(timezone.utc)))
        if not candidates:
            raise GeoResolutionError("NOT_FOUND")
        if len(candidates) > 1:
            raise GeoResolutionError("AMBIGUOUS_GEO_TARGET")
        self.cache[key] = candidates[0]
        return candidates[0]
