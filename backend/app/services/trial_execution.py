from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.models.entities import ProviderCall, SerpResultRow, SerpSnapshot
from app.providers.contracts import SerpRequest
from app.services.normalization import root_domain

def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

def persist_trial_serp(db, *, run, run_candidate, candidate_entity_id, keyword,
                       location_name, country_code, language_code, depth, result,
                       estimated_cost, actual_cost=None, request_key="trial-serp"):
    started = utc_now()
    response_cost = (result.raw or {}).get("cost") if isinstance(result.raw, dict) else None
    response = (result.raw or {}).get("response", result.raw or {}) if isinstance(result.raw, dict) else {}
    task_status = response.get("status_code") if isinstance(response, dict) else None
    valid = task_status in (None, 20000)
    raw_payload = {**(result.raw or {}), "_nicheforge_evidence_status": "VALID" if valid else "INVALID_PROVIDER_RESPONSE"}
    snapshot = SerpSnapshot(candidate_id="pipeline", candidate_entity_id=candidate_entity_id,
        provider="dataforseo_trial", source_kind="dataforseo_trial", keyword=keyword,
        location_name=location_name, language_code=language_code, country_code=country_code,
        requested_depth=depth, raw_payload=raw_payload, fetched_at=started,
        fresh_until=started + timedelta(days=7))
    db.add(snapshot); db.flush()
    for item in (result.organic[:depth] if valid else []):
        db.add(SerpResultRow(snapshot_id=snapshot.id, position=item.position,
            title=item.title, url=item.url, root_domain=root_domain(item.url),
            result_type="organic"))
    call = ProviderCall(provider="dataforseo", execution_mode="TRIAL", stage="serp",
        operation="live_regular", request_cache_key=request_key, outcome="success" if valid else "error",
        source_kind="dataforseo_trial", run_id=run.id, run_candidate_id=run_candidate.id,
        started_at=started, finished_at=utc_now(), estimated_cost=estimated_cost,
        actual_cost=actual_cost, currency="USD",
        error_category=None if valid else "provider_response",
        error_message=None if valid else f"DataForSEO application status {task_status}")
    db.add(call)
    run.estimated_cost = (run.estimated_cost or 0) + estimated_cost
    if actual_cost is not None:
        run.actual_cost = (run.actual_cost or 0) + actual_cost
    db.flush()
    return snapshot, call


async def execute_trial_serp(db, *, run, run_candidate, candidate_entity_id,
                             city, state, keyword, language_code="en", country_code="US",
                             depth=None, estimated_cost, approved=True, provider=None,
                             location_resolver=None):
    """Execute exactly one mocked/injected Trial SERP request and persist canonical evidence."""
    from app.providers.dataforseo import DataForSEOSerpProvider
    from app.providers.runtime_config import DataForSEOConfig, ProviderMode

    depth = depth or run.organic_depth
    context = dict(run.configuration_snapshot or {})
    if context.get("dataforseo_mode") != ProviderMode.TRIAL.value:
        raise ValueError("Trial execution requires a Run snapshotted in TRIAL mode")
    config = DataForSEOConfig(mode=ProviderMode.TRIAL,
                              remaining_trial_budget=context.get("remaining_trial_budget"),
                              standard_serp_cost=context.get("standard_serp_cost", estimated_cost),
                              credentials_configured=True)
    config.validate_paid_execution(estimated_cost, approved)
    provider = provider or DataForSEOSerpProvider("injected", "injected", mode=ProviderMode.TRIAL,
                                                   location_resolver=location_resolver)
    result = (await provider.fetch([SerpRequest(keyword, f"{city}, {state}, United States", language_code, depth)]))[0]
    raw = result.raw or {}
    actual_cost = raw.get("cost") if isinstance(raw, dict) else None
    return persist_trial_serp(db, run=run, run_candidate=run_candidate,
        candidate_entity_id=candidate_entity_id, keyword=keyword,
        location_name=f"{city}, {state}, United States", country_code=country_code,
        language_code=language_code, depth=depth, result=result,
        estimated_cost=estimated_cost, actual_cost=actual_cost)
