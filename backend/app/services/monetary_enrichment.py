"""Shared provider-currency to USD enrichment for keyword metrics."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from sqlalchemy.orm import Session
from app.services.currency_normalization import FxRate, normalize_to_usd
from app.services.fx_evidence import resolve_persisted_fx

@dataclass(frozen=True)
class UsdMetrics:
    usd_cpc: float | None
    usd_low_bid: float | None
    usd_high_bid: float | None
    fx_rate: float | None
    fx_rate_date: str | None
    fx_source: str | None

def resolve_usd_metrics(db: Session, *, provider_currency: str | None, cpc: float | None, low_bid: float | None, high_bid: float | None, customer_id: str | None = None, fx_rate: FxRate | None = None) -> UsdMetrics:
    if not provider_currency:
        return UsdMetrics(None, None, None, None, None, None)
    rate = fx_rate
    if provider_currency.upper() != "USD" and rate is None:
        rate = resolve_persisted_fx(db, provider_currency, "USD")
    values = [normalize_to_usd(x, provider_currency, rate=rate) for x in (cpc, low_bid, high_bid)]
    chosen = next((x[1] for x in values if x[1]), None)
    return UsdMetrics(*(x[0] for x in values), chosen.rate if chosen else None, chosen.rate_date if chosen else None, chosen.source if chosen else None)
