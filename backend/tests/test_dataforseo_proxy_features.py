import asyncio

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.entities import City, Project, CandidateEntity, ProjectCandidate, Run, RunCandidate, SerpSnapshot, SerpResultRow, ProviderCall, ProviderCache, ProxyBacklinkFeatureEvidence
from app.providers.contracts import AuthorityTarget
from app.providers.dataforseo_backlinks import DataForSEOBacklinkSummaryProvider
from app.services.identity import canonical_identity, identity_key
from app.services.proxy_authority import enrich_backlink_features, select_interesting_backlink_rows
from app.services.calibration_selector import select_calibration_sample, select_round2_calibration_sample
from app.services.calibration_consolidation import import_ahrefs_evidence


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


def test_calibration_selector_deduplicates_and_prioritizes_disagreement_without_network():
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine)
    with Session(engine) as db:
        rows = [SerpResultRow(snapshot_id="s", position=i, url=f"https://{domain}/", root_domain=domain) for i, domain in enumerate(("weak-example.com", "strong-example.com", "border-example.com", "weak-example.com"), 1)]
        db.add_all(rows)
        db.add_all([
            __import__("app.models.entities", fromlist=["ProxyAuthorityEvidence"]).ProxyAuthorityEvidence(root_domain="weak-example.com", target_url="https://weak-example.com", domain_rating=3.0, fetched_at=__import__("datetime").datetime.utcnow()),
            __import__("app.models.entities", fromlist=["ProxyAuthorityEvidence"]).ProxyAuthorityEvidence(root_domain="strong-example.com", target_url="https://strong-example.com", domain_rating=75.0, fetched_at=__import__("datetime").datetime.utcnow()),
            __import__("app.models.entities", fromlist=["ProxyAuthorityEvidence"]).ProxyAuthorityEvidence(root_domain="border-example.com", target_url="https://border-example.com", domain_rating=25.0, fetched_at=__import__("datetime").datetime.utcnow()),
            ProxyBacklinkFeatureEvidence(target_domain="weak-example.com", rank=283, mapping_status="mapped"),
        ])
        db.commit()
        result = select_calibration_sample(db, rows, limit=3)
        assert [item.domain for item in result] == ["weak-example.com", "border-example.com", "strong-example.com"]
        assert result[0].disagreement is True
        assert len({item.domain for item in result}) == 3


def test_calibration_evidence_import_preserves_provenance_cache_and_avoids_provider_calls():
    source_engine = create_engine("sqlite:///:memory:"); target_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(source_engine); Base.metadata.create_all(target_engine)
    with Session(source_engine) as source, Session(target_engine) as target:
        observed = __import__("app.models.entities", fromlist=["ProxyAuthorityEvidence"]).ProxyAuthorityEvidence(id="source-evidence", target_url="https://imported.example.com", root_domain="imported.example.com", domain_rating=3.6, source_kind="ahrefs_api", request_metadata={"endpoint": "/v3/public/domain-rating-free"})
        source.add(observed); source.commit()
        imported = import_ahrefs_evidence(source, target, "source.db")
        assert len(imported) == 1
        assert imported[0].id == "source-evidence"
        assert imported[0].source_kind == "imported_calibration"
        assert imported[0].request_metadata["imported_from_database"] == "source.db"
        assert target.query(ProviderCall).count() == 0
        assert target.query(ProviderCache).count() == 1
        assert import_ahrefs_evidence(source, target, "source.db") == []


def test_round2_selector_excludes_labels_and_prioritizes_boundary_without_network():
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine)
    with Session(engine) as db:
        rows = [SerpResultRow(snapshot_id="s", position=i, url=f"https://round{i}.com/", root_domain=f"round{i}.com") for i in range(1, 4)]
        db.add_all(rows)
        Evidence = __import__("app.models.entities", fromlist=["ProxyAuthorityEvidence"]).ProxyAuthorityEvidence
        db.add_all([Evidence(root_domain="round1.com", target_url="https://round1.com", domain_rating=12), Evidence(root_domain="round2.com", target_url="https://round2.com", domain_rating=4), Evidence(root_domain="round3.com", target_url="https://round3.com", domain_rating=80)])
        db.commit()
        result = select_round2_calibration_sample(db, rows, {"round1.com"}, 3)
        assert [item.domain for item in result] == ["round2.com", "round3.com"]


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
        first = asyncio.run(enrich_backlink_features(db, run, rc, [row]))
        first[0].mapping_status = "unrecoverable_raw_missing"
        db.commit()
        second = asyncio.run(enrich_backlink_features(db, run, rc, [row]))
        third = asyncio.run(enrich_backlink_features(db, run, rc, [row]))
        cache = db.scalar(select(__import__("app.models.entities", fromlist=["ProviderCache"]).ProviderCache))
        assert provider.calls == 2
        assert first[0].id != second[0].id == third[0].id
        assert cache.evidence_id == second[0].id
        assert db.get(ProxyBacklinkFeatureEvidence, first[0].id).mapping_status == "unrecoverable_raw_missing"
        assert second[0].provider == "dataforseo" and second[0].rank == 99
        assert db.query(ProviderCall).filter_by(provider="dataforseo", operation="PROVIDER_ACQUISITION").count() == 2
        assert db.query(ProviderCall).filter_by(provider="dataforseo", operation="CACHE_REUSE").count() == 1
        assert db.query(ProxyBacklinkFeatureEvidence).count() == 2


def test_backlink_enrichment_queue_selects_only_weak_domains_without_network():
    domains = ["foo.com", "bar.net", "baz.org"]
    rows = [SerpResultRow(snapshot_id="s", position=i, url=f"https://{domain}/", root_domain=domain) for i, domain in enumerate(domains, 1)]
    selected = select_interesting_backlink_rows(rows, {"foo.com": 8, "bar.net": 45, "baz.org": None}, {"foo.com": 40, "bar.net": 10, "baz.org": None})
    assert [row.root_domain for row in selected] == ["foo.com", "bar.net"]
