import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.entities import CandidateEntity, City, Project, ProjectCandidate, ProviderCall, Run, RunCandidate, SerpResultRow, SerpSnapshot
from app.providers.contracts import AuthorityResult, KeywordMetricResult, OrganicResult, SerpResult
from app.services.identity import canonical_identity, identity_key
from app.services.run_pipeline import execute_run


class SV:
    async def fetch(self, requests):
        return [KeywordMetricResult(r.keyword, 500, provider="mock") for r in requests]


class SERP:
    def __init__(self, count=10): self.calls = 0; self.count = count
    async def fetch(self, requests):
        self.calls += 1
        return [SerpResult(r.keyword, [OrganicResult(i, f"Result {i}", f"https://site-{i}.example/page") for i in range(1, self.count + 1)], "dataforseo", raw={"response": {"status_code": 20000}, "cost": 0.1379}) for r in requests]


class AUTH:
    async def fetch(self, targets):
        return [AuthorityResult(t.url, t.root_domain, 5, provider="mock") for t in targets]


def setup_run():
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine); db = Session(engine)
    city = City(name="Testville", state_code="NY", population=50000, population_vintage="test")
    project = Project(name="SERP telemetry", profile_snapshot={}); db.add_all([city, project]); db.flush()
    ident = canonical_identity("tree service", "US-TEST")
    entity = CandidateEntity(canonical_identity=ident, identity_key=identity_key(ident), service_term_normalized="tree service", city_id=city.id, canonical_keyword="tree service")
    db.add(entity); db.flush(); pc = ProjectCandidate(project_id=project.id, candidate_entity_id=entity.id, display_keyword="tree service"); db.add(pc); db.flush()
    run = Run(project_id=project.id, min_population=1, max_population=100000, min_search_volume=1, da_threshold=10, required_low_da_count=0, organic_depth=10, minimum_organic_rows=9, minimum_organic_coverage=.9); db.add(run); db.commit()
    return db, run, pc


@pytest.mark.asyncio
async def test_execute_run_serp_acquisition_persists_cost_and_coverage(monkeypatch):
    import app.services.run_pipeline as pipeline
    db, run, pc = setup_run(); serp = SERP(10)
    monkeypatch.setattr(pipeline, "search_volume_provider", lambda: SV()); monkeypatch.setattr(pipeline, "serp_provider", lambda: serp); monkeypatch.setattr(pipeline, "authority_provider", lambda: AUTH())
    await execute_run(db, run.id, [pc.id])
    call = db.query(ProviderCall).filter(ProviderCall.stage == "serp", ProviderCall.operation == "PROVIDER_ACQUISITION").one()
    snap = db.query(SerpSnapshot).one()
    assert serp.calls == 1 and db.query(SerpResultRow).filter_by(snapshot_id=snap.id).count() == 10
    assert call.http_request_count == 1 and call.items_returned_count == 1
    assert call.actual_cost == 0.1379 and call.currency == "USD" and call.cost_confidence == "PROVIDER_REPORTED"
    assert call.metadata_json["evidence_state"] == "VALID" and call.metadata_json["observed_depth"] == 10


@pytest.mark.asyncio
async def test_execute_run_serp_telemetry_failure_does_not_duplicate_request(monkeypatch):
    import app.services.run_pipeline as pipeline
    db, run, pc = setup_run(); serp = SERP(10)
    monkeypatch.setattr(pipeline, "search_volume_provider", lambda: SV()); monkeypatch.setattr(pipeline, "serp_provider", lambda: serp); monkeypatch.setattr(pipeline, "authority_provider", lambda: AUTH())
    monkeypatch.setattr(pipeline, "ProviderCall", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("telemetry construction failure")))
    await execute_run(db, run.id, [pc.id])
    assert serp.calls == 1 and db.query(SerpSnapshot).count() == 1 and db.query(SerpResultRow).count() == 10
    assert db.query(RunCandidate).count() == 1
    db.execute(select(RunCandidate.id).where(RunCandidate.run_id == run.id)).scalar_one()
