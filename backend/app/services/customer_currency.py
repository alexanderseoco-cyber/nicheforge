"""Customer-currency resolution without geo or implicit-default inference."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.entities import ProviderCustomerMetadata

@dataclass(frozen=True)
class CustomerCurrencyResolution:
    customer_id: str
    currency_code: str | None
    source: str
    cache_hit: bool

def resolve_cached_customer_currency(db: Session, *, provider: str, customer_id: str | None, override: str | None = None) -> CustomerCurrencyResolution:
    """Use only verified metadata or explicit override; never invoke transport."""
    identity = customer_id or ""
    if override:
        return CustomerCurrencyResolution(identity, override.upper(), "CONFIG_OVERRIDE", False)
    if not customer_id:
        return CustomerCurrencyResolution(identity, None, "UNKNOWN", False)
    metadata = db.query(ProviderCustomerMetadata).filter_by(provider=provider, customer_id=customer_id).first()
    if metadata and metadata.currency_code and (metadata.fresh_until is None or metadata.fresh_until > datetime.utcnow()):
        return CustomerCurrencyResolution(customer_id, metadata.currency_code.upper(), "GOOGLE_CUSTOMER_METADATA", True)
    return CustomerCurrencyResolution(customer_id, None, "UNKNOWN", False)
