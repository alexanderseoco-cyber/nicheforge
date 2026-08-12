from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routes import router
from app.db.base import Base
from app.db.session import get_db
from app.models.entities import KeywordMetricEvidence, KeywordMetricValidationHandoff


def test_handoff_references_exact_evidence_and_preserves_subset():
    engine=create_engine("sqlite://", connect_args={"check_same_thread":False}, poolclass=StaticPool); Base.metadata.create_all(engine); db=Session(engine)
    evidence=KeywordMetricEvidence(query_id="q", submitted_keyword="term", provider_keyword="term exact", normalized_keyword="term", provider="imported", source_kind="imported", location_target={"geo":"x"}, mapping_status="MAPPED")
    db.add(evidence); db.commit()
    app=FastAPI(); app.include_router(router); app.dependency_overrides[get_db]=lambda:db
    response=TestClient(app).post("/api/v1/keyword-metrics/send-to-validation", json={"evidence_ids":[evidence.id],"validation_profile":{"min_search_volume":260}})
    assert response.status_code==200 and response.json()["selected_count"]==1 and response.json()["provider_requests"]==0
    handoff=db.query(KeywordMetricValidationHandoff).one(); assert handoff.evidence_id==evidence.id; assert handoff.provider_keyword=="term exact"; assert handoff.validation_profile_snapshot["min_search_volume"]==260
    app.dependency_overrides.clear(); db.close()
