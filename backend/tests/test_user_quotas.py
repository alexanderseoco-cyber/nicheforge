from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.entities import User, UserProviderQuota, UserQuotaBonus
from app.services.auth import hash_password
from app.services.user_quotas import allowance, reserve, finish


def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_user_allowance_reservation_consumption_and_release():
    db = session()
    user = User(email="quota@example.com", password_hash=hash_password("a" * 12), role="USER", status="ACTIVE")
    db.add(user); db.flush()
    db.add(UserProviderQuota(user_id=user.id, provider="google_ads", daily_allowance=5, enabled=True)); db.commit()
    reservation = reserve(db, user.id, "google_ads", 3, "batch-1", None, None)
    assert allowance(db, user.id)["available"] == 2
    finish(db, reservation, 1)
    db.commit()
    assert allowance(db, user.id)["consumed"] == 1
    assert allowance(db, user.id)["reserved"] == 0


def test_expired_bonus_is_not_available_and_active_bonus_is_concurrency_safe_boundary():
    db = session()
    user = User(email="bonus@example.com", password_hash=hash_password("b" * 12), role="USER", status="ACTIVE")
    admin = User(email="admin@example.com", password_hash=hash_password("c" * 12), role="ADMIN", status="ACTIVE")
    db.add_all([user, admin]); db.flush()
    db.add(UserProviderQuota(user_id=user.id, provider="google_ads", daily_allowance=1, enabled=True))
    db.add(UserQuotaBonus(user_id=user.id, provider="google_ads", operations=4, expires_at=datetime.utcnow() - timedelta(seconds=1), created_by=admin.id))
    db.commit()
    assert allowance(db, user.id)["available"] == 1
    db.add(UserQuotaBonus(user_id=user.id, provider="google_ads", operations=2, expires_at=datetime.utcnow() + timedelta(hours=1), created_by=admin.id)); db.commit()
    reservation = reserve(db, user.id, "google_ads", 3, "batch-2", None, None)
    assert reservation.reserved_operations == 3
