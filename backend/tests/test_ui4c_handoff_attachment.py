from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routes import router
from app.db.base import Base
from app.db.session import get_db
from app.models.entities import City, KeywordMetricEvidence, KeywordMetricValidationHandoff, ProjectCandidate


def test_existing_project_handoff_attachment_is_idempotent_and_conflict_safe():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine); db = Session(engine)
    db.add(City(name="Albany", state_code="GA", population=70000, population_vintage="test")); db.flush()
    target = {"city": "Albany", "state_code": "GA", "geo_target_ids": ["1015247"]}
    e1 = KeywordMetricEvidence(query_id="q1", submitted_keyword="tree services albany", normalized_keyword="tree services albany", provider="mock", source_kind="mock", avg_monthly_searches=390, location_target=target, country_code="US", language_code="en", mapping_status="MAPPED")
    db.add(e1); db.flush()
    h1 = KeywordMetricValidationHandoff(evidence_id=e1.id, submitted_keyword=e1.submitted_keyword, provider="mock", location_target=target, country_code="US", language_code="en")
    db.add(h1); db.commit()
    app = FastAPI(); app.include_router(router); app.dependency_overrides[get_db] = lambda: db; client = TestClient(app)
    project = client.post("/api/v1/projects", json={"name": "UI-4C"}).json()
    first = client.post(f"/api/v1/projects/{project['id']}/handoffs/attach", json={"handoff_ids": [h1.id]})
    assert first.status_code == 200 and first.json()["created_count"] == 1
    candidate = db.query(ProjectCandidate).one(); assert candidate.search_volume_evidence_id == e1.id
    second = client.post(f"/api/v1/projects/{project['id']}/handoffs/attach", json={"handoff_ids": [h1.id]})
    assert second.status_code == 200 and second.json()["existing_count"] == 1
    e2 = KeywordMetricEvidence(query_id="q2", submitted_keyword=e1.submitted_keyword, normalized_keyword=e1.normalized_keyword, provider="mock", source_kind="mock", avg_monthly_searches=999, location_target=target, country_code="US", language_code="en", mapping_status="MAPPED")
    db.add(e2); db.flush(); h2 = KeywordMetricValidationHandoff(evidence_id=e2.id, submitted_keyword=e2.submitted_keyword, provider="mock", location_target=target, country_code="US", language_code="en"); db.add(h2); db.commit()
    conflict = client.post(f"/api/v1/projects/{project['id']}/handoffs/attach", json={"handoff_ids": [h2.id]})
    assert conflict.status_code == 409
    db.refresh(candidate); assert candidate.search_volume_evidence_id == e1.id
    assert db.query(KeywordMetricEvidence).count() == 2


def test_country_targeted_localized_handoff_resolves_unique_city_without_provider_call():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine); db = Session(engine)
    db.add(City(name="Albany", state_code="GA", population=70000, population_vintage="test")); db.flush()
    evidence = KeywordMetricEvidence(query_id="q-local", submitted_keyword="tree services albany", normalized_keyword="tree services albany", provider="mock", source_kind="mock", avg_monthly_searches=390, location_target={"country_code": "US"}, country_code="US", language_code="en", mapping_status="MAPPED")
    db.add(evidence); db.flush()
    handoff = KeywordMetricValidationHandoff(evidence_id=evidence.id, submitted_keyword=evidence.submitted_keyword, provider="mock", location_target={"country_code": "US"}, country_code="US", language_code="en")
    db.add(handoff); db.commit()
    app = FastAPI(); app.include_router(router); app.dependency_overrides[get_db] = lambda: db; client = TestClient(app)
    project = client.post("/api/v1/projects", json={"name": "UI-4C localized"}).json()
    response = client.post(f"/api/v1/projects/{project['id']}/handoffs/attach", json={"handoff_ids": [handoff.id]})
    assert response.status_code == 200
    candidate = db.query(ProjectCandidate).one()
    assert response.json()["created_count"] == 1
    assert candidate.search_volume_evidence_id == evidence.id


def test_ambiguous_localized_handoff_returns_candidates_without_guessing():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine); db = Session(engine)
    db.add_all([City(name="Albany", state_code="GA", population=70000, population_vintage="test"), City(name="Albany", state_code="NY", population=70000, population_vintage="test")]); db.flush()
    evidence = KeywordMetricEvidence(query_id="q-ambiguous", submitted_keyword="tree services albany", normalized_keyword="tree services albany", provider="mock", source_kind="mock", avg_monthly_searches=390, location_target={"country_code": "US"}, country_code="US", language_code="en", mapping_status="MAPPED")
    db.add(evidence); db.flush(); handoff = KeywordMetricValidationHandoff(evidence_id=evidence.id, submitted_keyword=evidence.submitted_keyword, provider="mock", location_target={"country_code": "US"}, country_code="US", language_code="en"); db.add(handoff); db.commit()
    app = FastAPI(); app.include_router(router); app.dependency_overrides[get_db] = lambda: db; client = TestClient(app); project = client.post("/api/v1/projects", json={"name": "ambiguous"}).json()
    response = client.post(f"/api/v1/projects/{project['id']}/handoffs/attach", json={"handoff_ids": [handoff.id]})
    assert response.status_code == 200
    assert response.json()["summary"]["needs_location"] == 1
    assert response.json()["results"][0]["status"] == "LOCAL_LOCATION_REQUIRED"
    assert {row["state"] for row in response.json()["results"][0]["city_candidates"]} == {"GA", "NY"}
