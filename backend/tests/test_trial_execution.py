import asyncio
import httpx
from app.services.trial_execution import persist_trial_serp, execute_trial_serp
from app.models.entities import Run, RunCandidate, ProviderCall
from app.providers.contracts import OrganicResult
from app.providers.dataforseo import DataForSEOSerpProvider
from app.providers.location_resolution import DataForSEOLocationResolver

def test_trial_persistence_and_cost_are_canonical():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.db.base import Base
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine)
    db_session = Session(engine)
    run = Run(project_id="p", min_population=1, max_population=2, min_search_volume=0,
              da_threshold=10, required_low_da_count=0, organic_depth=2,
              configuration_snapshot={"dataforseo_mode": "TRIAL"})
    db_session.add(run); db_session.flush()
    rc = RunCandidate(run_id=run.id, project_candidate_id="c"); db_session.add(rc); db_session.flush()
    result = type("R", (), {"raw": {"cost": 0.25}, "organic": [OrganicResult(1, "A", "https://a.example")]})()
    snapshot, call = persist_trial_serp(db_session, run=run, run_candidate=rc,
        candidate_entity_id="e", keyword="term", location_name="Salina, Kansas, United States",
        country_code="US", language_code="en", depth=2, result=result, estimated_cost=0.25)
    assert snapshot.provider == "dataforseo_trial" and call.execution_mode == "TRIAL"
    assert call.actual_cost is None and run.estimated_cost == 0.25
    assert db_session.query(ProviderCall).count() == 1
    db_session.close()


def test_trial_end_to_end_resolves_exact_location_routes_trial_and_persists_cost(monkeypatch):
    from app.db.base import Base
    from app.models.entities import ProviderCall, SerpResultRow, SerpSnapshot
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine)
    db = Session(engine)
    run = Run(project_id="p", min_population=1, max_population=2, min_search_volume=0,
              da_threshold=10, required_low_da_count=0, organic_depth=2,
              configuration_snapshot={"dataforseo_mode": "TRIAL", "remaining_trial_budget": 2.0,
                                      "standard_serp_cost": 0.25})
    db.add(run); db.flush(); rc = RunCandidate(run_id=run.id, project_candidate_id="c")
    db.add(rc); db.flush(); requests = []

    async def handler(request):
        requests.append(request)
        if request.url.path.endswith("/locations/us"):
            return httpx.Response(200, json={"tasks": [{"result": [{
                "location_name": "Salina, Kansas, United States", "location_code": 101}]}]})
        return httpx.Response(200, json={"tasks": [{"cost": 0.19, "result": [{"items": [
            {"type": "organic", "rank_absolute": 1, "title": "A", "url": "https://a.example"},
            {"type": "organic", "rank_absolute": 2, "title": "B", "url": "https://b.example"},
        ]}]}]})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))
    resolver = DataForSEOLocationResolver(DataForSEOSerpProvider("l", "p").client)
    provider = DataForSEOSerpProvider("l", "p", mode="TRIAL", location_resolver=resolver)
    snapshot, call = asyncio.run(execute_trial_serp(db, run=run, run_candidate=rc,
        candidate_entity_id="e", city="Salina", state="Kansas", keyword="term",
        estimated_cost=0.25, provider=provider, location_resolver=resolver))
    assert requests[0].url == "https://api.dataforseo.com/v3/serp/google/locations/us"
    assert requests[1].url == "https://api.dataforseo.com/v3/serp/google/organic/live/regular"
    assert requests[1].content.find(b'"location_code":101') >= 0
    assert b'location_name' not in requests[1].content
    assert snapshot.provider == snapshot.source_kind == "dataforseo_trial"
    assert db.query(SerpResultRow).count() == 2
    assert call.provider == "dataforseo" and call.execution_mode == "TRIAL"
    assert call.run_id == run.id and call.run_candidate_id == rc.id
    assert call.estimated_cost == 0.25 and call.actual_cost == 0.19
    assert call.started_at is not None and call.finished_at is not None and call.outcome == "success"
    assert run.configuration_snapshot["remaining_trial_budget"] == 2.0
    db.close()


def test_trial_location_cache_reuse_and_no_cross_mode_fallback(monkeypatch):
    import asyncio
    calls = {"locations": 0}
    class Client:
        async def get(self, path):
            calls["locations"] += 1
            return {"tasks": [{"result": [{"location_name": "Salina, Kansas, United States", "location_code": 101}]}]}
    resolver = DataForSEOLocationResolver(Client())
    asyncio.run(resolver.resolve("Salina", "Kansas")); asyncio.run(resolver.resolve("Salina", "Kansas"))
    assert calls["locations"] == 1
    from app.providers.dataforseo import DataForSEOSandboxSerpProvider
    try:
        DataForSEOSerpProvider("l", "p", mode="SANDBOX")
    except ValueError as exc:
        assert "Sandbox" in str(exc)
    else:
        raise AssertionError("Trial adapter must not fall back to Sandbox")
    assert DataForSEOSandboxSerpProvider.provider == "dataforseo_sandbox"


def test_application_error_is_auditable_but_not_valid_serp_evidence():
    from app.db.base import Base
    from app.models.entities import ProviderCall, SerpResultRow, SerpSnapshot
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine)
    db = Session(engine)
    run = Run(project_id="p", min_population=1, max_population=2, min_search_volume=0,
              da_threshold=10, required_low_da_count=0, organic_depth=2,
              configuration_snapshot={"dataforseo_mode": "TRIAL"})
    db.add(run); db.flush(); rc = RunCandidate(run_id=run.id, project_candidate_id="c"); db.add(rc); db.flush()
    result = type("R", (), {"raw": {"response": {"status_code": 40501, "status_message": "Invalid Field"}, "cost": 0.0}, "organic": []})()
    snapshot, call = persist_trial_serp(db, run=run, run_candidate=rc, candidate_entity_id="e", keyword="term",
        location_name="Salina,Kansas,United States", country_code="US", language_code="en", depth=2,
        result=result, estimated_cost=0.002, actual_cost=0.0)
    db.commit()
    assert snapshot.raw_payload["_nicheforge_evidence_status"] == "INVALID_PROVIDER_RESPONSE"
    assert db.query(SerpResultRow).count() == 0
    assert call.outcome == "error" and call.actual_cost == 0.0
    db.close()
