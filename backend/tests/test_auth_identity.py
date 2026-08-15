from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.auth_routes import router
from app.db.session import get_db
from app.models.entities import Base, User
from app.services.auth import hash_password, issue_access_token, verify_password
from app.api import auth_routes


def _setup(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine); db = Session(engine)
    app = FastAPI(); app.include_router(router); app.dependency_overrides[get_db] = lambda: db
    settings = SimpleNamespace(auth_secret="local-test-secret", auth_access_token_lifetime_seconds=900, auth_refresh_token_lifetime_seconds=3600)
    monkeypatch.setattr(auth_routes, "get_settings", lambda: settings)
    return TestClient(app), db


def test_password_hash_is_not_plaintext_and_verifies():
    encoded = hash_password("a sufficiently strong password")
    assert encoded != "a sufficiently strong password"
    assert verify_password("a sufficiently strong password", encoded)
    assert not verify_password("wrong password", encoded)


def test_login_refresh_rotation_and_revocation(monkeypatch):
    client, db = _setup(monkeypatch)
    user = User(email="admin@example.com", password_hash=hash_password("a sufficiently strong password"), role="ADMIN", status="ACTIVE")
    db.add(user); db.commit()
    login = client.post("/api/v1/auth/login", json={"email": " ADMIN@EXAMPLE.COM ", "password": "a sufficiently strong password"})
    assert login.status_code == 200
    first = login.json(); refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert refreshed.status_code == 200 and refreshed.json()["refresh_token"] != first["refresh_token"]
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]}).status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {refreshed.json()['access_token']}"}).status_code == 200


def test_disabled_user_cannot_use_existing_access_token(monkeypatch):
    client, db = _setup(monkeypatch)
    user = User(email="user@example.com", password_hash=hash_password("a sufficiently strong password"), role="USER", status="ACTIVE")
    db.add(user); db.commit()
    token = issue_access_token(user.id, user.role, "local-test-secret", 900)
    user.status = "DISABLED"; db.commit()
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 403


def test_last_active_admin_cannot_be_demoted(monkeypatch):
    client, db = _setup(monkeypatch)
    admin = User(email="admin@example.com", password_hash=hash_password("a sufficiently strong password"), role="ADMIN", status="ACTIVE")
    db.add(admin); db.commit()
    token = issue_access_token(admin.id, admin.role, "local-test-secret", 900)
    response = client.patch(f"/api/v1/admin/users/{admin.id}", headers={"Authorization": f"Bearer {token}"}, json={"role": "USER"})
    assert response.status_code == 409
