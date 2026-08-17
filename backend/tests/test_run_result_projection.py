from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.routes import _run_response
from app.db.base import Base
from app.models.entities import CandidateEntity, KeywordMetricEvidence, Project, ProjectCandidate, Run, RunCandidate
from app.services.identity import canonical_identity, identity_key


def test_run_response_prefers_canonical_keyword_metric_evidence():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    project = Project(name="projection")
    db.add(project)
    db.flush()
    canonical = canonical_identity("stylish text generator", "US")
    entity = CandidateEntity(
        canonical_identity=canonical, identity_key=identity_key(canonical),
        service_term_normalized="stylish text generator", canonical_keyword="stylish text generator",
    )
    db.add(entity)
    db.flush()
    evidence = KeywordMetricEvidence(
        query_id="q1", submitted_keyword="stylish text generator",
        provider_keyword="stylish text generator", normalized_keyword="stylish text generator",
        location_name="United States", location_target={"country_code": "US"},
        language_code="en", country_code="US", provider="google_ads", source_kind="live_api",
        avg_monthly_searches=74000, competition_index=4, monthly_history=[],
        raw_payload={}, fetched_at=datetime.utcnow(),
    )
    db.add(evidence)
    db.flush()
    candidate = ProjectCandidate(project_id=project.id, candidate_entity_id=entity.id, display_keyword=evidence.submitted_keyword)
    db.add(candidate)
    db.flush()
    run = Run(project_id=project.id, status="COMPLETED", min_population=0, max_population=999999,
              min_search_volume=260, da_threshold=10, required_low_da_count=4, organic_depth=10,
              country_code="US", language_code="en")
    db.add(run)
    db.flush()
    db.add(RunCandidate(run_id=run.id, project_candidate_id=candidate.id,
                        validation_scope="GENERAL_NICHE", keyword_metric_evidence_id=evidence.id,
                        status="PASS", finished_at=datetime.utcnow()))
    db.commit()

    result = _run_response(db, run)["candidate_results"][0]
    assert result["search_volume"] == "PASS"
    assert result["search_volume_value"] == 74000
    assert result["search_volume_provider"] == "google_ads"


def test_run_response_keeps_legacy_search_volume_evidence_compatible():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    project = Project(name="legacy")
    db.add(project)
    db.flush()
    canonical = canonical_identity("legacy keyword", "US")
    entity = CandidateEntity(canonical_identity=canonical, identity_key=identity_key(canonical),
                             service_term_normalized="legacy keyword", canonical_keyword="legacy keyword")
    db.add(entity)
    db.flush()
    from app.models.entities import SearchVolumeEvidence
    evidence = SearchVolumeEvidence(candidate_entity_id=entity.id, keyword="legacy keyword",
                                    location_name="United States", provider="mock", source_kind="mock",
                                    avg_monthly_searches=0)
    db.add(evidence)
    db.flush()
    candidate = ProjectCandidate(project_id=project.id, candidate_entity_id=entity.id, display_keyword="legacy keyword")
    db.add(candidate)
    db.flush()
    run = Run(project_id=project.id, status="COMPLETED", min_population=0, max_population=999999,
              min_search_volume=0, da_threshold=10, required_low_da_count=4, organic_depth=10,
              country_code="US", language_code="en")
    db.add(run)
    db.flush()
    db.add(RunCandidate(run_id=run.id, project_candidate_id=candidate.id,
                        search_volume_evidence_id=evidence.id, status="PASS", finished_at=datetime.utcnow()))
    db.commit()

    result = _run_response(db, run)["candidate_results"][0]
    assert result["search_volume"] == "PASS"
    assert result["search_volume_value"] == 0
