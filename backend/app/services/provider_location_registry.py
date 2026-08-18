from __future__ import annotations

from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import City, ProviderLocationIdentity
from app.providers.location_resolution import US_STATE_NAMES


class ProviderLocationUnresolved(ValueError):
    code = "PROVIDER_LOCATION_UNRESOLVED"


def _norm(value: str | None) -> str:
    return (value or "").strip().casefold()


def find_verified_mapping(db: Session, city: City, provider: str = "dataforseo") -> ProviderLocationIdentity | None:
    stmt = select(ProviderLocationIdentity).where(
        ProviderLocationIdentity.city_id == city.id,
        ProviderLocationIdentity.provider == provider,
        ProviderLocationIdentity.verified.is_(True),
        ProviderLocationIdentity.city_name == city.name,
        ProviderLocationIdentity.state_code == city.state_code,
    )
    matches = db.scalars(stmt).all()
    return matches[0] if len(matches) == 1 else None


def require_verified_mapping(db: Session, city: City, provider: str = "dataforseo") -> ProviderLocationIdentity:
    mapping = find_verified_mapping(db, city, provider)
    if mapping is None:
        raise ProviderLocationUnresolved(
            f"{ProviderLocationUnresolved.code}: {city.name}, {city.state_code}, {provider}"
        )
    return mapping


def persist_verified_mapping(db: Session, city: City, *, provider: str, location_code: int,
                             provider_location_name: str, country_code: str = "US",
                             location_type: str = "City", source: str = "PROVIDER_CATALOG",
                             fetched_at: datetime | None = None,
                             imported_at: datetime | None = None) -> ProviderLocationIdentity:
    if source not in {"PROVIDER_CATALOG", "MANUAL_VERIFIED", "IMPORTED", "LEGACY"}:
        raise ValueError("unsupported provider location source")
    state_name = next((name for name, code in US_STATE_NAMES.items() if code == city.state_code.upper()), city.state_code)
    provider_identity = _norm(provider_location_name)
    if _norm(city.name) not in provider_identity or (_norm(city.state_code) not in provider_identity and _norm(state_name) not in provider_identity):
        raise ValueError("provider location identity does not match city/state")
    mapping = ProviderLocationIdentity(
        city_id=city.id, provider=provider, location_code=location_code,
        provider_location_name=provider_location_name, country_code=country_code,
        state_code=city.state_code, city_name=city.name, location_type=location_type,
        source=source, verified=True, fetched_at=fetched_at, imported_at=imported_at,
    )
    db.add(mapping)
    db.flush()
    return mapping
