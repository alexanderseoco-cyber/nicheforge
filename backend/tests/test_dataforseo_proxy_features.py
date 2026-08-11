import asyncio

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.entities import City, Project, CandidateEntity, ProjectCandidate, Run, RunCandidate, SerpSnapshot, SerpResultRow, ProviderCall, ProxyBacklinkFeatureEvidence
from app.providers.contracts import AuthorityTarget
from app.providers.dataforseo_backlinks import DataForSEOBacklinkSummaryProvider
from app.services.identity import canonical_identity, identity_key
from app.services.proxy_authority import enrich_backlink_features


def test_dataforseo_backlink_provider_maps_one_response_to_multiple_features(monkeypatch):
    class Client:
        async def post(self, path, payload):
            assert path == "/v3/backlinks/bulk_pages_summary/live"
            assert payload == [{"targets": ["example.com", "other.com"]}]
            return {"status_code": 20000, "status_message": "Ok.", "tasks": [{"status_code": 20000, "cost": 0.02, "result": [{"items": [
                {"url": "https://example.com/", "rank": 123, "backlinks": 10, "referring_domains": 4, "referring_main_domains": 3, "referring_ips": 2, "referring_subnets": 2, "referring_domains_nofollow": 1, "referring_main_domains_nofollow": 1, "backlinks_spam_score": 5},
                {"url": "https://other.com/page", "rank": 456, "backlinks": 20, "referring_domains": 8, "referring_main_domains": 7}
            ]}]}]}
    provider = DataForSEOBacklinkSummaryProvider("login", "password", enabled=True, live_approved=True, estimated_cost=0.03, budget=0.03)
    provider.client = Client()
    results = asyncio.run(provider.fetch([AuthorityTarget("https://example.com", "example.com"), AuthorityTarget("https://other.com", "other.com")]))
    assert [(item.target, item.rank, item.referring_main_domains) for item in results] == [("example.com", 123, 3), ("other.com", 456, 7)]
    assert results[0].actual_cost == 0.02
    assert results[0].mapping_status == "mapped"
    assert results[0].response_raw["tasks"][0]["result"][0]["items"][0]["url"] == "https://example.com/"
    assert "Authorization" not in str(results[0].response_raw)


def test_dataforseo_backlink_provider_marks_unmatched_items_without_fabricating_metrics(monkeypatch):
    class Client:
        async def post(self, path, payload):
            return {"status_code": 20000, "status_message": "Ok.", "tasks": [{"cost": 0.02, "result": [{"items": [{"url": "https://present.com/", "rank": 10}]}]}]}

    provider = DataForSEOBacklinkSummaryProvider("login", "password", enabled=True, live_approved=True, estimated_cost=0.02, budget=0.03)
    provider.client = Client()
    results = asyncio.run(provider.fetch([
        AuthorityTarget("https://present.com", "present.com"),
        AuthorityTarget("https://missing.com", "missing.com"),
    ]))
    assert results[0].mapping_status == "mapped"
    assert results[1].mapping_status == "provider_missing_or_empty"
    assert results[1].rank is None and results[1].backlinks is None
    assert results[1].mapping_error


def test_dataforseo_backlink_guard_blocks_before_transport():
    provider = DataForSEOBacklinkSummaryProvider("login", "password")
    try:
        asyncio.run(provider.fetch([AuthorityTarget("https://example.com", "example.com")]))
    except RuntimeError as exc:
        assert "DATAFORSEO_BACKLINK_PROXY_ENABLED" in str(exc)
    else:
        raise AssertionError("backlink enrichment was not blocked")


def test_dataforseo_backlink_budget_guard_blocks_over_budget():
    provider = DataForSEOBacklinkSummaryProvider("login", "password", enabled=True, live_approved=True, estimated_cost=0.031, budget=0.03)
    try:
        asyncio.run(provider.fetch([AuthorityTarget("https://example.com", "example.com")]))
    except RuntimeError as exc:
        assert "budget" in str(exc)
    else:
        raise AssertionError("over-budget backlink request was not blocked")


def test_backlink_features_are_separate_and_cacheable(monkeypatch):
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine)
    class Provider:
        operation = "backlinks_bulk_pages_summary_live"; endpoint = "/v3/backlinks/bulk_pages_summary/live"; estimated_cost = 0.02
        budget = 0.03
        calls = 0
        async def fetch(self, targets):
            self.calls += 1
            return [type("R", (), {"rank": 99, "backlinks": 12, "referring_domains": 4, "referring_main_domains": 3, "referring_ips": 2, "referring_subnets": 2, "referring_domains_nofollow": 1, "referring_main_domains_nofollow": 1, "backlinks_spam_score": 3, "raw": {"target": targets[0].root_domain}, "actual_cost": 0.02, "api_status_code": 20000, "api_status_message": "Ok."})() for _ in targets]
    provider = Provider()
    monkeypatch.setattr("app.services.proxy_authority.dataforseo_backlink_proxy_provider", lambda: provider)
    with Session(engine) as db:
        project = Project(name="proxy", profile_snapshot={}); city = City(name="Salina", state_code="KS", population=47000, population_vintage="test"); db.add_all([project, city]); db.flush()
        ident = canonical_identity("pest control", "US-1"); entity = CandidateEntity(canonical_identity=ident, identity_key=identity_key(ident), service_term_normalized="pest control", city_id=city.id, canonical_keyword="pest control salina ks"); db.add(entity); db.flush()
        pc = ProjectCandidate(project_id=project.id, candidate_entity_id=entity.id, display_keyword=entity.canonical_keyword); db.add(pc); db.flush()
        run = Run(project_id=project.id, run_type="PROXY", min_population=1, max_population=100000, min_search_volume=0, da_threshold=10, required_low_da_count=4, organic_depth=1); db.add(run); db.flush(); rc = RunCandidate(run_id=run.id, project_candidate_id=pc.id); db.add(rc); db.flush()
        snap = SerpSnapshot(candidate_id="pipeline", candidate_entity_id=entity.id, provider="mock", source_kind="mock", keyword=entity.canonical_keyword, location_name="Salina, KS", requested_depth=1); db.add(snap); db.flush(); row = SerpResultRow(snapshot_id=snap.id, position=1, url="https://example.com/page", root_domain="example.com"); db.add(row); db.commit()
        first = asyncio.run(enrich_backlink_features(db, run, rc, [row])); second = asyncio.run(enrich_backlink_features(db, run, rc, [row]))
        assert provider.calls == 1
        assert first[0].id == second[0].id
        assert first[0].provider == "dataforseo" and first[0].rank == 99
        assert db.query(ProviderCall).filter_by(provider="dataforseo").count() == 1
        assert db.query(ProxyBacklinkFeatureEvidence).count() == 1
