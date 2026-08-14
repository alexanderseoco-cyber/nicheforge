"""Durable, date-aware FX evidence resolution."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.entities import FxRateEvidence
from app.services.currency_normalization import FxRate


def persist_fx_rate(db: Session, rate: FxRate, *, mode: str = "latest", requested_as_of: date | None = None, freshness_days: int = 7) -> FxRateEvidence:
    row = db.query(FxRateEvidence).filter_by(
        source_currency=rate.source_currency.upper(), target_currency=rate.target_currency.upper(),
        mode=mode, requested_as_of_date=requested_as_of, provider=rate.source,
    ).first()
    if row is None:
        row = FxRateEvidence(source_currency=rate.source_currency.upper(), target_currency=rate.target_currency.upper(), mode=mode, requested_as_of_date=requested_as_of, provider=rate.source)
        db.add(row)
    row.rate = Decimal(str(rate.rate))
    row.provider_effective_date = date.fromisoformat(rate.rate_date) if rate.rate_date else None
    row.fetched_at = datetime.utcnow()
    row.fresh_until = row.fetched_at + timedelta(days=freshness_days)
    row.provenance = {"source": rate.source, "rate_direction": f"1 {rate.source_currency.upper()} = rate {rate.target_currency.upper()}"}
    db.commit(); db.refresh(row)
    return row


def resolve_persisted_fx(db: Session, source: str, target: str, *, mode: str = "latest", as_of: date | None = None, now: datetime | None = None) -> FxRate | None:
    now = now or datetime.utcnow()
    query = db.query(FxRateEvidence).filter_by(source_currency=source.upper(), target_currency=target.upper(), mode=mode, provider="exchangerate_api_open")
    if mode == "historical": query = query.filter_by(requested_as_of_date=as_of)
    row = query.order_by(FxRateEvidence.fetched_at.desc()).first()
    if not row or (row.fresh_until and row.fresh_until <= now): return None
    return FxRate(row.source_currency, row.target_currency, float(row.rate), row.provider_effective_date.isoformat() if row.provider_effective_date else "", row.provider)
