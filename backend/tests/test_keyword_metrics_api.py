from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from fastapi import FastAPI
from app.api.routes import router
from app.models.entities import KeywordMetricEvidence, ProviderCall, User
from app.services.auth import hash_password, issue_access_token
from app.api import routes
from app.api import auth_routes

app = FastAPI()
app.include_router(router)


def _client(monkeypatch, provider="mock"):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = Session(engine)
    app.dependency_overrides[get_db] = lambda: db
    settings = SimpleNamespace(keyword_metrics_provider=provider, google_ads_enabled=False, google_ads_live_approved=False, google_ads_customer_id=None, google_ads_currency_code=None, auth_secret="test-secret", auth_access_token_lifetime_seconds=900, auth_refresh_token_lifetime_seconds=3600)
    monkeypatch.setattr(routes, "get_settings", lambda: settings, raising=False)
    monkeypatch.setattr(auth_routes, "get_settings", lambda: settings, raising=False)
    monkeypatch.setattr("app.providers.factory.get_settings", lambda: settings)
    return TestClient(app, raise_server_exceptions=False), db


def test_preview_is_non_transporting(monkeypatch):
    client, db = _client(monkeypatch)
    response = client.post("/api/v1/keyword-metrics/preview", json={"keywords": ["term", "term"], "provider": "mock", "target": {"location_name": "United States", "country_code": "US"}})
    assert response.status_code == 200
    assert response.json()["transport_would_occur"] is False
    assert response.json()["planned_rpc_count"] == 1
    assert response.json()["fresh_cache_savings"] == 0
    app.dependency_overrides.clear(); db.close()


def test_research_with_mock_provider(monkeypatch):
    client, db = _client(monkeypatch)
    response = client.post("/api/v1/keyword-metrics/research", json={"keywords": ["term"], "provider": "mock", "target": {"location_name": "United States", "country_code": "US"}})
    assert response.status_code == 200
    assert response.json()["mapped_count"] == 1
    call = db.query(ProviderCall).one()
    assert call.stage == "keyword_metrics" and call.outcome == "SUCCESS"
    assert call.execution_mode == "MOCK" and call.operation_count == 0
    app.dependency_overrides.clear(); db.close()


def test_unknown_provider_is_rejected(monkeypatch):
    client, db = _client(monkeypatch, "not-a-provider")
    response = client.post("/api/v1/keyword-metrics/preview", json={"keywords": ["term"], "provider": "not-a-provider", "target": {"location_name": "United States", "country_code": "US"}})
    assert response.status_code == 500
    app.dependency_overrides.clear(); db.close()


def test_unmapped_response_is_serialized(monkeypatch):
    client, db = _client(monkeypatch, "imported")
    response = client.post("/api/v1/keyword-metrics/research", json={"keywords": ["term"], "provider": "imported", "target": {"location_name": "United States", "country_code": "US"}})
    assert response.status_code == 200
    assert response.json()["unmapped_count"] == 1
    app.dependency_overrides.clear(); db.close()


def test_get_evidence_retrieval(monkeypatch):
    client, db = _client(monkeypatch)
    evidence = KeywordMetricEvidence(query_id="q", submitted_keyword="term", provider_keyword="term", normalized_keyword="term", provider="mock", source_kind="mock", mapping_status="MAPPED")
    db.add(evidence); db.commit()
    response = client.get(f"/api/v1/keyword-metrics/{evidence.id}")
    assert response.status_code == 200 and response.json()["submitted_keyword"] == "term"
    app.dependency_overrides.clear(); db.close()


def test_provider_telemetry_summary_is_local_only(monkeypatch):
    client, db = _client(monkeypatch)
    admin = User(email="admin@example.com", password_hash=hash_password("a sufficiently strong password"), role="ADMIN", status="ACTIVE")
    db.add(admin); db.commit()
    token = issue_access_token(admin.id, admin.role, "test-secret", 900)
    response = client.get("/api/v1/keyword-metrics/provider-telemetry", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["actual_attempts"] == 0
    assert response.json()["consumed_operations"] == 0
    app.dependency_overrides.clear(); db.close()
