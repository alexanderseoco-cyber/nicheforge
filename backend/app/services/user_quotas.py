"""Authenticated user/provider allowance and atomic run reservations.

ProviderCall.operation_count remains the source of truth for external usage;
UserProviderUsage only attributes that usage to the authenticated user.
"""
from datetime import datetime, timedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.entities import UserProviderQuota, UserQuotaBonus, RunReservation, UserProviderUsage, ProviderCall, uid

DEFAULT_PROVIDER = "google_ads"

def _window_start():
    return datetime.utcnow() - timedelta(hours=24)

def _quota(db: Session, user_id: str, provider: str):
    row = db.execute(select(UserProviderQuota).where(UserProviderQuota.user_id == user_id, UserProviderQuota.provider == provider).with_for_update()).scalar_one_or_none()
    return row

def allowance(db: Session, user_id: str, provider: str = DEFAULT_PROVIDER):
    quota = _quota(db, user_id, provider)
    configured = quota.daily_allowance if quota else 0
    enabled = quota.enabled if quota else False
    now = datetime.utcnow()
    bonus = db.scalar(select(func.coalesce(func.sum(UserQuotaBonus.operations), 0)).where(UserQuotaBonus.user_id == user_id, UserQuotaBonus.provider == provider, UserQuotaBonus.expires_at > now)) or 0
    consumed = db.scalar(select(func.coalesce(func.sum(UserProviderUsage.operation_count), 0)).where(UserProviderUsage.user_id == user_id, UserProviderUsage.provider == provider, UserProviderUsage.recorded_at >= _window_start())) or 0
    reserved = db.scalar(select(func.coalesce(func.sum(RunReservation.reserved_operations - RunReservation.consumed_operations), 0)).where(RunReservation.user_id == user_id, RunReservation.provider == provider, RunReservation.status == "ACTIVE")) or 0
    return {"configured": configured, "bonus": int(bonus), "consumed": int(consumed), "reserved": int(reserved), "available": max(0, int(configured + bonus - consumed - reserved)), "enabled": bool(enabled)}

def provider_capacity(db: Session, provider: str, customer_id: str | None, configured_budget: int | None):
    if configured_budget is None:
        return None
    used = db.scalar(select(func.coalesce(func.sum(ProviderCall.operation_count), 0)).where(ProviderCall.provider == provider, ProviderCall.customer_id == customer_id, ProviderCall.started_at >= _window_start(), ProviderCall.operation_count == 1)) or 0
    active = db.scalar(select(func.coalesce(func.sum(RunReservation.reserved_operations - RunReservation.consumed_operations), 0)).where(RunReservation.provider == provider, RunReservation.status == "ACTIVE")) or 0
    return max(0, int(configured_budget - used - active))

def reserve(db: Session, user_id: str, provider: str, requested: int, batch_id: str | None, configured_budget: int | None, customer_id: str | None):
    requested = max(0, int(requested)); info = allowance(db, user_id, provider); capacity = provider_capacity(db, provider, customer_id, configured_budget)
    effective = info["available"] if capacity is None else min(info["available"], capacity)
    if not info["enabled"]: raise ValueError("USER_PROVIDER_DISABLED")
    if requested > effective: raise ValueError("USER_QUOTA_EXCEEDED" if info["available"] < requested else "PROVIDER_CAPACITY_EXCEEDED")
    row = RunReservation(user_id=user_id, provider=provider, batch_id=batch_id, reserved_operations=requested, consumed_operations=0, status="ACTIVE")
    db.add(row); db.flush(); return row

def finish(db: Session, reservation: RunReservation, consumed: int, provider_call_ids: list[str] | None = None):
    consumed = max(0, int(consumed));
    if consumed > reservation.reserved_operations: raise ValueError("RESERVATION_EXCEEDED")
    reservation.consumed_operations = consumed; reservation.status = "COMPLETED"; reservation.completed_at = datetime.utcnow()
    ids = provider_call_ids or []
    for call_id in ids:
        db.add(UserProviderUsage(user_id=reservation.user_id, provider=reservation.provider, reservation_id=reservation.id, provider_call_id=call_id, operation_count=1))
    if consumed and not ids:
        db.add(UserProviderUsage(user_id=reservation.user_id, provider=reservation.provider, reservation_id=reservation.id, operation_count=consumed))
    db.flush()

def snapshot(db: Session, user_id: str, provider: str = DEFAULT_PROVIDER):
    return allowance(db, user_id, provider)
