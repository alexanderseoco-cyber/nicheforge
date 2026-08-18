import asyncio

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.entities import Base, CandidateEntity, City, Project, ProjectCandidate, ProviderCall, ProxyAuthorityEvidence, Run, RunCandidate, SerpResultRow
from app.providers.contracts import ProxyAuthorityResult
from app.services.identity import canonical_identity, identity_key
from app.services.proxy_authority import evaluate_run_candidate_proxy


def _context():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    city = City(name="Testville", state_code="NY", population=50000, population_vintage="test")
    project = Project(name="Ahrefs telemetry", profile_snapshot={})
    db.add_all([city, project]); db.flush()
    ident = canonical_identity("tree service", "US-TEST")
    entity = CandidateEntity(canonical_identity=ident, identity_key=identity_key(ident), service_term_normalized="tree service", city_id=city.id, canonical_keyword="tree service")
    db.add(entity); db.flush()
    candidate = ProjectCandidate(project_id=project.id, candidate_entity_id=entity.id, display_keyword="tree service")
    db.add(candidate); db.flush()
    run = Run(project_id=project.id, min_population=1, max_population=100000, min_search_volume=1, da_threshold=10, required_low_da_count=0, organic_depth=1)
    db.add(run); db.flush()
    rc = RunCandidate(run_id=run.id, project_candidate_id=candidate.id); db.add(rc); db.flush()
    row = SerpResultRow(snapshot_id="snapshot", position=1, url="https://example.com/page", root_domain="example.com")
    db.add(row); db.commit()
    return db, run, rc, row


class FakeAhrefs:
    calls = 0
    async def fetch(self, targets):
        self.calls += 1
        target = targets[0]
        return [ProxyAuthorityResult(target.url, target.root_domain, 23.5, provider="ahrefs", raw={"domain_rating": {"domain_rating": 23.5}})]


class FakeAhrefsMissing(FakeAhrefs):
    async def fetch(self, targets):
        self.calls += 1
        target = targets[0]
        return [ProxyAuthorityResult(target.url, target.root_domain, None, provider="ahrefs", raw={})]


class FakeAhrefsZero(FakeAhrefs):
    async def fetch(self, targets):
        self.calls += 1
        target = targets[0]
        return [ProxyAuthorityResult(target.url, target.root_domain, 0, provider="ahrefs", raw={"domain_rating": {"domain_rating": 0}})]


class FailingAhrefs:
    calls = 0
    async def fetch(self, targets):
        self.calls += 1
        raise RuntimeError("provider failure")


def test_ahrefs_acquisition_telemetry_and_reuse(monkeypatch):
    db, run, rc, row = _context()
    provider = FakeAhrefs()
    monkeypatch.setattr("app.services.proxy_authority.ahrefs_proxy_provider", lambda: provider)
    asyncio.run(evaluate_run_candidate_proxy(db, run, rc, [row]))
    acquisition = db.query(ProviderCall).filter_by(operation="PROVIDER_ACQUISITION").one()
    assert provider.calls == 1
    assert acquisition.provider_item_count == 1 and acquisition.http_request_count == 1
    assert acquisition.items_returned_count == 1 and acquisition.evidence_created_count == 1
    assert acquisition.actual_cost is None and acquisition.currency is None and acquisition.cost_confidence == "UNKNOWN"

    asyncio.run(evaluate_run_candidate_proxy(db, run, rc, [row]))
    reuse = db.query(ProviderCall).filter_by(operation="CACHE_REUSE").one()
    assert provider.calls == 1
    assert reuse.provider_item_count == 0 and reuse.http_request_count == 0 and reuse.evidence_reused_count == 1
    assert reuse.paid_attempt is False and reuse.cost_confidence == "NOT_APPLICABLE"


def test_ahrefs_telemetry_failure_does_not_repeat_provider_call(monkeypatch):
    db, run, rc, row = _context()
    provider = FakeAhrefs()
    monkeypatch.setattr("app.services.proxy_authority.ahrefs_proxy_provider", lambda: provider)
    monkeypatch.setattr("app.services.proxy_authority.ProviderCall", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("telemetry failure")))
    asyncio.run(evaluate_run_candidate_proxy(db, run, rc, [row]))
    assert provider.calls == 1
    assert db.execute(select(SerpResultRow.id)).scalar_one() == row.id
    assert db.query(ProviderCall).count() == 0


def test_ahrefs_provider_error_is_one_attempt_without_evidence(monkeypatch):
    db, run, rc, row = _context()
    provider = FailingAhrefs()
    monkeypatch.setattr("app.services.proxy_authority.ahrefs_proxy_provider", lambda: provider)
    try:
        asyncio.run(evaluate_run_candidate_proxy(db, run, rc, [row]))
    except RuntimeError:
        pass
    else:
        raise AssertionError("provider error was not propagated by the existing production path")
    call = db.query(ProviderCall).one()
    assert provider.calls == 1 and call.http_request_count == 1 and call.http_request_sent is True
    assert call.provider_item_count == 1 and call.items_returned_count == 0
    assert call.items_failed_count == 1 and call.evidence_missing_count == 1
    assert call.actual_cost is None and call.estimated_cost is None and call.currency is None
    assert db.query(ProxyAuthorityEvidence).count() == 0


def test_ahrefs_missing_dr_is_successful_operation_without_fake_zero(monkeypatch):
    db, run, rc, row = _context()
    provider = FakeAhrefsMissing()
    monkeypatch.setattr("app.services.proxy_authority.ahrefs_proxy_provider", lambda: provider)
    asyncio.run(evaluate_run_candidate_proxy(db, run, rc, [row]))
    call = db.query(ProviderCall).one()
    assert provider.calls == 1 and call.outcome == "success"
    assert call.items_returned_count == 0 and call.items_failed_count == 1
    assert call.evidence_created_count == 0 and call.evidence_missing_count == 1
    assert db.query(ProxyAuthorityEvidence).count() == 0


def test_ahrefs_zero_dr_is_distinct_from_missing(monkeypatch):
    db, run, rc, row = _context()
    provider = FakeAhrefsZero()
    monkeypatch.setattr("app.services.proxy_authority.ahrefs_proxy_provider", lambda: provider)
    asyncio.run(evaluate_run_candidate_proxy(db, run, rc, [row]))
    call = db.query(ProviderCall).one()
    assert call.items_returned_count == 1 and call.evidence_created_count == 1 and call.evidence_missing_count == 0
    assert db.query(ProxyAuthorityEvidence).one().domain_rating == 0
