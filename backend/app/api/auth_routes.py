from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import User, UserSession, UserProviderQuota, UserQuotaBonus
from app.services.user_quotas import snapshot, DEFAULT_PROVIDER
from app.services.auth import decode_access_token, hash_password, issue_access_token, new_refresh_token, normalize_email, refresh_token_hash, verify_password
from app.services.auth_rate_limit import AuthAttemptLimiter

router = APIRouter(prefix="/api/v1")
login_limiter = AuthAttemptLimiter()
class LoginRequest(BaseModel):
    email: str
    password: str
    client_type: str = "WEB"
class RefreshRequest(BaseModel):
    refresh_token: str
class UserCreateRequest(BaseModel):
    email: str
    password: str = Field(min_length=12)
    role: str = "USER"
    display_name: str | None = None
class UserUpdateRequest(BaseModel):
    role: str | None = None
    status: str | None = None
    email: str | None = None
    display_name: str | None = None

def _settings():
    s = get_settings()
    if not s.auth_secret: raise HTTPException(503, "Authentication is not configured")
    return s
def _safe_user(user: User) -> dict:
    return {"id": user.id, "email": user.email, "display_name": user.display_name, "role": user.role, "status": user.status, "created_at": user.created_at, "last_login_at": user.last_login_at}
def _tokens(db, user: User, client_type: str, s):
    raw = new_refresh_token(); now = datetime.utcnow()
    db.add(UserSession(user_id=user.id, refresh_token_hash=refresh_token_hash(raw), expires_at=now + timedelta(seconds=s.auth_refresh_token_lifetime_seconds), client_type=client_type))
    return {"access_token": issue_access_token(user.id, user.role, s.auth_secret, s.auth_access_token_lifetime_seconds), "refresh_token": raw, "token_type": "bearer", "expires_in": s.auth_access_token_lifetime_seconds}

@router.post("/auth/login")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    s = _settings()
    client_key = f"{request.client.host if request.client else 'unknown'}:{payload.email.strip().casefold()}"
    if not login_limiter.allow(client_key): raise HTTPException(429, "Too many login attempts; try again later")
    try: email = normalize_email(payload.email)
    except ValueError: raise HTTPException(401, "Invalid email or password")
    user = db.query(User).filter_by(email=email).first()
    if not user or user.status != "ACTIVE" or not verify_password(payload.password, user.password_hash): raise HTTPException(401, "Invalid email or password")
    user.last_login_at = datetime.utcnow(); result = _tokens(db, user, payload.client_type, s); db.commit(); return result

@router.post("/auth/refresh")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    s = _settings(); row = db.query(UserSession).filter_by(refresh_token_hash=refresh_token_hash(payload.refresh_token)).first(); now = datetime.utcnow()
    if not row or row.revoked_at or row.expires_at <= now: raise HTTPException(401, "Invalid refresh token")
    user = db.get(User, row.user_id)
    if not user or user.status != "ACTIVE": raise HTTPException(401, "Invalid refresh token")
    row.revoked_at = now; row.last_used_at = now; result = _tokens(db, user, row.client_type, s); db.commit(); return result

def get_current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    s = _settings()
    if not authorization or not authorization.lower().startswith("bearer "): raise HTTPException(401, "Authentication required")
    try: payload = decode_access_token(authorization.split(" ", 1)[1], s.auth_secret)
    except ValueError: raise HTTPException(401, "Authentication required")
    user = db.get(User, payload["sub"])
    if not user or user.status != "ACTIVE": raise HTTPException(403, "Account is disabled")
    return user
def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "ADMIN": raise HTTPException(403, "Administrator access required")
    return user
@router.post("/auth/logout")
def logout(payload: RefreshRequest, db: Session = Depends(get_db)):
    row = db.query(UserSession).filter_by(refresh_token_hash=refresh_token_hash(payload.refresh_token)).first()
    if row and not row.revoked_at: row.revoked_at = datetime.utcnow(); db.commit()
    return {"status": "logged_out"}
@router.get("/auth/me")
def me(user: User = Depends(get_current_user)): return _safe_user(user)
@router.get("/admin/users")
def list_users(_: User = Depends(require_admin), db: Session = Depends(get_db)): return [_safe_user(user) for user in db.query(User).order_by(User.created_at).all()]
@router.post("/admin/users")
def create_user(payload: UserCreateRequest, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    try: email = normalize_email(payload.email)
    except ValueError as exc: raise HTTPException(422, str(exc))
    if payload.role not in {"ADMIN", "USER"}: raise HTTPException(422, "Invalid role")
    if db.query(User).filter_by(email=email).first(): raise HTTPException(409, "Email already exists")
    user = User(email=email, display_name=payload.display_name, password_hash=hash_password(payload.password), role=payload.role, status="ACTIVE"); db.add(user); db.commit(); db.refresh(user); return _safe_user(user)
@router.get("/admin/users/{user_id}")
def get_user(user_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user: raise HTTPException(404, "User not found")
    return _safe_user(user)
@router.patch("/admin/users/{user_id}")
def update_user(user_id: str, payload: UserUpdateRequest, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user: raise HTTPException(404, "User not found")
    if payload.email is not None:
        email = normalize_email(payload.email)
        if db.query(User).filter(User.email == email, User.id != user.id).first(): raise HTTPException(409, "Email already exists")
        user.email = email
    if payload.role is not None:
        if payload.role not in {"ADMIN", "USER"}: raise HTTPException(422, "Invalid role")
        if user.role == "ADMIN" and payload.role != "ADMIN" and db.query(User).filter_by(role="ADMIN", status="ACTIVE").count() <= 1: raise HTTPException(409, "Cannot remove the last active administrator")
        user.role = payload.role
    if payload.status is not None:
        if payload.status not in {"ACTIVE", "DISABLED"}: raise HTTPException(422, "Invalid status")
        if user.role == "ADMIN" and payload.status != "ACTIVE" and db.query(User).filter_by(role="ADMIN", status="ACTIVE").count() <= 1: raise HTTPException(409, "Cannot disable the last active administrator")
        user.status = payload.status
    if payload.display_name is not None: user.display_name = payload.display_name
    db.commit(); db.refresh(user); return _safe_user(user)

class QuotaUpdateRequest(BaseModel):
    daily_allowance: int = Field(ge=0)
    enabled: bool = True
class BonusRequest(BaseModel):
    operations: int = Field(gt=0)
    expires_at: datetime
    reason: str | None = None

@router.get("/admin/users/{user_id}/quota")
def get_quota(user_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    if not db.get(User, user_id): raise HTTPException(404, "User not found")
    return {"user_id": user_id, "provider": DEFAULT_PROVIDER, **snapshot(db, user_id)}

@router.patch("/admin/users/{user_id}/quota")
def update_quota(user_id: str, payload: QuotaUpdateRequest, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    if not db.get(User, user_id): raise HTTPException(404, "User not found")
    row = db.query(UserProviderQuota).filter_by(user_id=user_id, provider=DEFAULT_PROVIDER).first()
    if row is None: row = UserProviderQuota(user_id=user_id, provider=DEFAULT_PROVIDER); db.add(row)
    row.daily_allowance = payload.daily_allowance; row.enabled = payload.enabled; db.commit()
    return {"user_id": user_id, "provider": DEFAULT_PROVIDER, **snapshot(db, user_id)}

@router.post("/admin/users/{user_id}/quota/bonuses")
def add_bonus(user_id: str, payload: BonusRequest, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if not db.get(User, user_id): raise HTTPException(404, "User not found")
    if payload.expires_at <= datetime.utcnow(): raise HTTPException(422, "Bonus must expire in the future")
    row = UserQuotaBonus(user_id=user_id, provider=DEFAULT_PROVIDER, operations=payload.operations, expires_at=payload.expires_at, reason=payload.reason, created_by=admin.id)
    db.add(row); db.commit(); db.refresh(row); return {"id": row.id, "user_id": user_id, "provider": DEFAULT_PROVIDER, "operations": row.operations, "expires_at": row.expires_at}

@router.get("/admin/users/{user_id}/usage")
def get_usage(user_id: str, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    if not db.get(User, user_id): raise HTTPException(404, "User not found")
    return {"user_id": user_id, "provider": DEFAULT_PROVIDER, **snapshot(db, user_id)}

@router.get("/me/quota")
def my_quota(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"user_id": user.id, "provider": DEFAULT_PROVIDER, **snapshot(db, user.id)}
