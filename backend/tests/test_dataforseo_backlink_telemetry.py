import asyncio

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.entities import City, Project, CandidateEntity, ProjectCandidate, Run, RunCandidate, SerpSnapshot, SerpResultRow, ProviderCall, ProxyBacklinkFeatureEvidence
from app.providers.contracts import BacklinkFeatureResult
from app.services.identity import canonical_identity, identity_key
from app.services.proxy_authority import enrich_backlink_features


def context(domains):
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine); db = Session(engine)
    city = City(name="Testville", state_code="NY", population=50000, population_vintage="test"); project = Project(name="C1E", profile_snapshot={}); db.add_all([city, project]); db.flush()
    ident = canonical_identity("tree service", "US-TEST"); entity = CandidateEntity(canonical_identity=ident, identity_key=identity_key(ident), service_term_normalized="tree service", city_id=city.id, canonical_keyword="tree service"); db.add(entity); db.flush()
    pc = ProjectCandidate(project_id=project.id, candidate_entity_id=entity.id, display_keyword="tree service"); db.add(pc); db.flush()
    run = Run(project_id=project.id, min_population=1, max_population=100000, min_search_volume=1, da_threshold=10, required_low_da_count=0, organic_depth=1); db.add(run); db.flush(); rc = RunCandidate(run_id=run.id, project_candidate_id=pc.id); db.add(rc); db.flush()
    snap = SerpSnapshot(candidate_id="c1e", candidate_entity_id=entity.id, provider="mock", source_kind="mock", keyword="tree service", location_name="Testville, NY", requested_depth=len(domains)); db.add(snap); db.flush()
    rows = []
    for i, domain in enumerate(domains, 1):
        row = SerpResultRow(snapshot_id=snap.id, position=i, url=f"https://{domain}/", root_domain=domain); db.add(row); rows.append(row)
    db.commit(); return db, run, rc, rows


class Fake:
    operation = "backlinks_bulk_pages_summary_live"; endpoint = "/v3/backlinks/bulk_pages_summary/live"
    def __init__(self, domains, missing=(), batch_size=2, costs=None): self.domains = domains; self.missing = set(missing); self.batch_size = batch_size; self.costs = costs or [0.01] * 10; self.calls = 0; self.last_batch_reports = []
    async def fetch(self, targets):
        self.last_batch_reports = []
        out = []
        for start in range(0, len(targets), self.batch_size):
            batch = targets[start:start+self.batch_size]; self.calls += 1; self.last_batch_reports.append({"targets": [t.root_domain for t in batch], "cost": self.costs[self.calls-1]})
            for target in batch:
                if target.root_domain in self.missing: continue
                out.append(BacklinkFeatureResult(target.root_domain, backlinks=0, referring_domains=0, referring_main_domains=0, referring_ips=0, referring_subnets=0, raw={"zero": True}, actual_cost=self.costs[self.calls-1]))
        return out


class Failing:
    last_batch_reports = []
    calls = 0
    async def fetch(self, targets):
        self.calls += 1; self.last_batch_reports = [{"targets": [t.root_domain for t in targets], "cost": None}]; raise RuntimeError("dataforseo failure")


def test_c1e_multibatch_partial_and_zero_metrics(monkeypatch):
    domains = [f"d{i}-example.com" for i in range(5)]; db, run, rc, rows = context(domains); provider = Fake(domains, missing={domains[3]}, batch_size=2, costs=[.01, .02, .03]); monkeypatch.setattr("app.services.proxy_authority.dataforseo_backlink_proxy_provider", lambda: provider)
    asyncio.run(enrich_backlink_features(db, run, rc, rows))
    calls = db.query(ProviderCall).filter_by(operation="PROVIDER_ACQUISITION").all()
    assert provider.calls == 3 and len(calls) == 3
    assert sum(c.provider_item_count for c in calls) == 5 and sum(c.http_request_count for c in calls) == 3
    assert sum(c.items_returned_count for c in calls) == 4 and sum(c.items_failed_count for c in calls) == 1
    assert sum(c.evidence_created_count for c in calls) == 4 and sum(c.evidence_missing_count for c in calls) == 1
    assert sum(c.actual_cost for c in calls) == .06 and all(c.estimated_cost is None for c in calls)
    assert db.query(ProxyBacklinkFeatureEvidence).filter_by(backlinks=0, referring_domains=0).count() == 4


def test_c1e_provider_error_records_attempt_and_preserves_exception(monkeypatch):
    db, run, rc, rows = context(["error.example"]); provider = Failing(); monkeypatch.setattr("app.services.proxy_authority.dataforseo_backlink_proxy_provider", lambda: provider)
    try: asyncio.run(enrich_backlink_features(db, run, rc, rows))
    except RuntimeError as exc: assert str(exc) == "dataforseo failure"
    else: raise AssertionError("provider exception was swallowed")
    call = db.query(ProviderCall).one(); assert provider.calls == 1 and call.outcome == "provider_error" and call.http_request_sent is True and call.evidence_missing_count == 1


def test_c1e_reuse_has_no_acquisition_or_http(monkeypatch):
    db, run, rc, rows = context(["reuse.example"]); first = Fake(["reuse.example"], batch_size=2); monkeypatch.setattr("app.services.proxy_authority.dataforseo_backlink_proxy_provider", lambda: first); asyncio.run(enrich_backlink_features(db, run, rc, rows))
    second = Fake(["reuse.example"], batch_size=2); monkeypatch.setattr("app.services.proxy_authority.dataforseo_backlink_proxy_provider", lambda: second); asyncio.run(enrich_backlink_features(db, run, rc, rows))
    assert second.calls == 0 and db.query(ProviderCall).filter_by(operation="PROVIDER_ACQUISITION").count() == 1
    reuse = db.query(ProviderCall).filter_by(operation="CACHE_REUSE").one(); assert reuse.provider_item_count == 0 and reuse.http_request_count == 0 and reuse.paid_attempt is False and reuse.evidence_reused_count == 1


def test_c1e_telemetry_failure_does_not_rollback_evidence(monkeypatch):
    domains = ["failure-example.com"]; db, run, rc, rows = context(domains); provider = Fake(domains); monkeypatch.setattr("app.services.proxy_authority.dataforseo_backlink_proxy_provider", lambda: provider)
    monkeypatch.setattr("app.services.proxy_authority.ProviderCall", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("telemetry construction failure")))
    result = asyncio.run(enrich_backlink_features(db, run, rc, rows))
    assert provider.calls == 1 and len(result) == 1 and result[0].backlinks == 0 and db.query(ProxyBacklinkFeatureEvidence).count() == 1
    assert db.execute(select(ProxyBacklinkFeatureEvidence.id)).scalar_one() == result[0].id


def test_c1e_partial_reuse_sends_only_unreused_domains(monkeypatch):
    domains = [f"partial-{i}-example.com" for i in range(5)]; db, run, rc, rows = context(domains); provider = Fake(domains[:2], batch_size=2); monkeypatch.setattr("app.services.proxy_authority.dataforseo_backlink_proxy_provider", lambda: provider)
    asyncio.run(enrich_backlink_features(db, run, rc, rows[:2]))
    provider2 = Fake(domains[2:], batch_size=2); monkeypatch.setattr("app.services.proxy_authority.dataforseo_backlink_proxy_provider", lambda: provider2)
    asyncio.run(enrich_backlink_features(db, run, rc, rows))
    reuse = db.query(ProviderCall).filter_by(operation="CACHE_REUSE").all(); acquisition = db.query(ProviderCall).filter_by(operation="PROVIDER_ACQUISITION").all()
    assert len(reuse) == 2 and sum(c.provider_item_count for c in acquisition) == 5 and sum(c.http_request_count for c in acquisition) == 3
    assert provider2.calls == 2


def test_c1e_mixed_aggregation_excludes_reuse_and_legacy_rows():
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine); db = Session(engine)
    db.add_all([
        ProviderCall(provider="dataforseo", stage="proxy_authority_enrichment", operation="PROVIDER_ACQUISITION", request_cache_key="a", outcome="success", source_kind="dataforseo_backlinks", logical_item_count=2, unique_target_count=2, provider_item_count=2, batch_count=1, http_request_count=1, items_returned_count=2, items_failed_count=0, evidence_created_count=2, evidence_missing_count=0, actual_cost=.12, estimated_cost=None, cost_confidence="PROVIDER_REPORTED"),
        ProviderCall(provider="dataforseo", stage="proxy_authority_enrichment", operation="PROVIDER_ACQUISITION", request_cache_key="b", outcome="provider_error", source_kind="dataforseo_backlinks", logical_item_count=1, unique_target_count=1, provider_item_count=1, batch_count=1, http_request_count=1, items_returned_count=0, items_failed_count=1, evidence_created_count=0, evidence_missing_count=1, actual_cost=None, estimated_cost=None, cost_confidence="UNKNOWN"),
        ProviderCall(provider="dataforseo", stage="proxy_authority_enrichment", operation="CACHE_REUSE", request_cache_key="r", outcome="cache_hit", source_kind="cache", logical_item_count=1, unique_target_count=1, provider_item_count=0, batch_count=0, http_request_count=0, evidence_reused_count=1, paid_attempt=False, actual_cost=None, estimated_cost=None, cost_confidence="NOT_APPLICABLE"),
        ProviderCall(provider="dataforseo", stage="proxy_authority_enrichment", operation="backlinks_bulk_pages_summary_live", request_cache_key="legacy", outcome="success", source_kind="dataforseo_backlinks", provider_item_count=3, http_request_count=1, actual_cost=.99),
    ]); db.commit()
    prospective = db.query(ProviderCall).filter(ProviderCall.provider == "dataforseo", ProviderCall.operation == "PROVIDER_ACQUISITION").all()
    reuse = db.query(ProviderCall).filter_by(operation="CACHE_REUSE").all()
    assert sum(c.http_request_count for c in prospective) == 2 and sum(c.provider_item_count for c in prospective) == 3
    assert sum(c.http_request_count for c in reuse) == 0 and sum(c.provider_item_count for c in reuse) == 0
    assert sum(c.actual_cost for c in prospective if c.actual_cost is not None) == .12
    assert db.query(ProviderCall).filter_by(operation="backlinks_bulk_pages_summary_live").one().actual_cost == .99


def test_c1e_provider_error_is_not_masked_by_telemetry_failure(monkeypatch):
    db, run, rc, rows = context(["masked-error.example"]); provider = Failing(); monkeypatch.setattr("app.services.proxy_authority.dataforseo_backlink_proxy_provider", lambda: provider)
    monkeypatch.setattr("app.services.proxy_authority.ProviderCall", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("telemetry failure")))
    try:
        asyncio.run(enrich_backlink_features(db, run, rc, rows))
    except RuntimeError as exc:
        assert str(exc) == "dataforseo failure"
    else:
        raise AssertionError("provider error was masked")
    assert provider.calls == 1
