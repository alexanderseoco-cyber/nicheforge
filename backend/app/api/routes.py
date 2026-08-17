import logging
import re
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import select, or_
from datetime import datetime

from app.db.session import get_db
from app.models.entities import ImportBatch, Project, City, Candidate, Run, RunCandidate, CandidateEntity, ProjectCandidate, SerpSnapshot, SerpResultRow, RunCandidateAuthorityEvidence, RunCandidateProxyAuthorityEvidence, RunCandidateBacklinkEvidence, AuthorityEvidence, ProxyAuthorityEvidence, ProxyBacklinkFeatureEvidence, KeywordMetricEvidence, SearchVolumeEvidence
from app.schemas.domain import (ProjectCreate, ProjectHandoffAttachRequest, ProjectHandoffAttachResponse, CandidateGenerateRequest, CandidateOut, RunRequest, RunCreate, RunOut, ValidationProfile, OverlayRequest, KeywordMetricsRequest, KeywordMetricsPreview, KeywordMetricsResearchResponse, KeywordMetricResultOut, KeywordMetricsHandoffRequest, KeywordMetricsHandoffResponse, KeywordMetricsBatchRequest, KeywordMetricsHandoffOut)
from app.services.normalization import normalize_keyword, build_keyword
from app.services.identity import canonical_identity, identity_key
from app.services.validation_scope import GENERAL_SCOPE, LOCAL_SCOPE, resolve_scope
from app.services.gates import population_gate
from app.services.pipeline import process_candidate
from app.providers.factory import authority_provider
from app.providers.contracts import AuthorityTarget
from app.services.normalization import root_domain
from app.services.run_pipeline import execute_run
from app.services.proxy_authority import evaluate_run_candidate_proxy
from app.services.recalculation import preview_recalculation, recalculate, ledger, candidate_history
from app.services.imports import export_candidate_history_csv, export_project_csv, export_run_csv, import_cities, import_keyword_export, import_manual_evidence, import_manual_moz_csv, import_moz, import_niches
from app.providers.factory import keyword_metrics_provider
from app.providers.contracts import KeywordMetricRequest
from app.models.entities import KeywordMetricQuery, KeywordMetricEvidence, KeywordMetricBatch, KeywordMetricValidationHandoff, ProviderCountryGeoMapping, KeywordOpportunityMetrics, ProviderCall
from app.services.keyword_metrics_batch import KeywordMetricsBatchOrchestrator
from app.services.keyword_metrics_multi_city import MultiCityKeywordMetricsOrchestrator, StructuredLocation
from app.providers.google_ads_geo import GoogleAdsGeoTargetResolver
from app.core.config import get_settings
from app.api.auth_routes import get_current_user
from app.models.entities import User, RunReservation
from app.services.user_quotas import reserve, finish, snapshot
from app.providers.keyword_metrics_safety import KeywordMetricsGuardError
from app.services.currency_normalization import normalize_to_usd
from app.services.customer_currency import resolve_cached_customer_currency
from app.services.monetary_enrichment import resolve_usd_metrics
from app.services.derived_metrics import calculate_derived_metrics
from app.api.auth_routes import require_admin

router = APIRouter(prefix="/api/v1")
logger = logging.getLogger(__name__)

@router.get("/app/capabilities")
def app_capabilities():
    settings = get_settings()
    return {"single_user_mode": bool(settings.nicheforge_single_user_mode)}

@router.get("/geo/countries")
def country_geo_capabilities(db: Session = Depends(get_db)):
    rows = db.query(ProviderCountryGeoMapping).filter_by(provider="google_ads", mapping_status="MAPPED").all()
    return [{"country_code": row.country_code, "provider": row.provider, "criterion_id": row.criterion_id, "resource_name": row.resource_name, "target_type": row.target_type, "status": row.mapping_status, "provenance": row.provenance} for row in rows]


def _metric_requests(payload: KeywordMetricsRequest):
    return [KeywordMetricRequest(keyword=k, location_name=payload.target.location_name,
        language_code=payload.target.language_code, country_code=payload.target.country_code,
        location_target=payload.target.location_target) for k in payload.keywords]


@router.post("/keyword-metrics/preview", response_model=KeywordMetricsPreview)
async def keyword_metrics_preview(payload: KeywordMetricsRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    requests = _metric_requests(payload)
    unique = {(r.keyword.strip().casefold(), r.location_name, r.language_code) for r in requests}
    provider = keyword_metrics_provider(provider_name=payload.provider)
    settings = get_settings()
    chunk_size = max(1, getattr(settings, "keyword_metrics_max_batch_size", 10_000))
    now = datetime.utcnow()
    fresh = 0
    for request in requests:
        cached = db.query(KeywordMetricEvidence).filter(
            KeywordMetricEvidence.provider == provider.provider_name,
            KeywordMetricEvidence.submitted_keyword == request.keyword,
            KeywordMetricEvidence.location_name == request.location_name,
            KeywordMetricEvidence.language_code == request.language_code,
            KeywordMetricEvidence.country_code == request.country_code,
        ).order_by(KeywordMetricEvidence.fetched_at.desc()).first()
        if cached and cached.fresh_until and cached.fresh_until > now and not payload.force_refresh:
            fresh += 1
    missing = max(0, len(unique) - fresh)
    planned = (missing + chunk_size - 1) // chunk_size
    budget = getattr(settings, "google_ads_daily_operation_budget", None)
    used = db.query(ProviderCall).filter(
        ProviderCall.provider == provider.provider_name,
        ProviderCall.customer_id == settings.google_ads_customer_id,
        ProviderCall.started_at >= datetime(now.year, now.month, now.day),
        ProviderCall.operation_count == 1,
    ).count() if provider.provider_name == "google_ads" else 0
    remaining = max(0, budget - used) if budget is not None else None
    user_allowance = snapshot(db, user.id, payload.provider)
    return KeywordMetricsPreview(submitted_count=len(requests), deduplicated_count=len(unique), cache_hits=fresh,
        provider_requests=0, estimated_cost=0.0, transport_would_occur=False, provider=provider.provider_name,
        total_combinations=len(unique), fresh_cache_savings=fresh,
        keywords_requiring_provider_evidence=missing, target_count=1,
        language_count=len({r.language_code for r in requests}), chunk_size=chunk_size,
        planned_rpc_count=planned, operation_budget_status=("CONFIGURED" if budget is not None else "UNKNOWN_UNVERIFIED"),
        provider_capacity_remaining=remaining,
        effective_executable_allowance=min(planned, remaining, user_allowance["available"]) if remaining is not None else min(planned, user_allowance["available"]))


@router.get("/keyword-metrics/provider-telemetry")
def keyword_metrics_provider_telemetry(_: object = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(ProviderCall).filter(ProviderCall.stage == "keyword_metrics").all()
    return {
        "provider": "google_ads",
        "actual_attempts": len(rows),
        "successful_attempts": sum(row.outcome == "SUCCESS" for row in rows),
        "provider_rejections": sum(row.outcome == "PROVIDER_REJECTED" for row in rows),
        "pre_provider_failures": sum(row.outcome == "NETWORK_FAILURE_BEFORE_PROVIDER" for row in rows),
        "budget_rejections": sum(row.outcome == "BUDGET_EXCEEDED" for row in rows),
        "consumed_operations": sum(row.operation_count or 0 for row in rows),
        "submitted_keywords": sum(row.submitted_keyword_count or 0 for row in rows),
    }


@router.post("/keyword-metrics/research", response_model=KeywordMetricsResearchResponse)
async def keyword_metrics_research(payload: KeywordMetricsRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    requests = _metric_requests(payload); provider = keyword_metrics_provider(provider_name=payload.provider)
    batch = KeywordMetricBatch(provider=provider.provider_name, submitted_count=len(requests), status="RUNNING")
    db.add(batch); db.flush()
    reservation = None
    try:
        settings = get_settings()
        planned = (len({r.keyword.strip().casefold() for r in requests}) + max(1, getattr(settings, "keyword_metrics_max_batch_size", 10_000)) - 1) // max(1, getattr(settings, "keyword_metrics_max_batch_size", 10_000))
        try:
            reservation = reserve(db, user.id, provider.provider_name, planned, batch.id, getattr(settings, "google_ads_daily_operation_budget", None), getattr(settings, "google_ads_customer_id", None))
        except ValueError as exc:
            db.rollback(); raise HTTPException(status_code=409, detail=str(exc)) from exc
        result = await KeywordMetricsBatchOrchestrator(
            provider, db=db, customer_id=settings.google_ads_customer_id
        ).execute(requests)
    except KeywordMetricsGuardError as exc:
        if reservation: finish(db, reservation, 0)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        if reservation: finish(db, reservation, 0)
        logger.exception("Keyword metrics research failed before response serialization")
        # Keep provider/runtime failures JSON-shaped so browser clients receive
        # a readable API error instead of a CORS-looking network failure.
        safe_type = type(exc).__name__
        raise HTTPException(status_code=502, detail=f"Google Ads search-volume request failed ({safe_type}).") from exc
    for request in requests:
        query = KeywordMetricQuery(submitted_keyword=request.keyword, normalized_keyword=request.keyword.strip().casefold(), location_name=request.location_name, location_target=request.location_target or {}, language_code=request.language_code, country_code=request.country_code, provider=provider.provider_name, status=result.mapping_status.get(request.keyword, "UNMAPPED"))
        db.add(query); db.flush(); item=result.results.get(request.keyword)
        evidence = None
        if item and result.mapping_status.get(request.keyword) != "UNMAPPED":
            # Never infer currency from the target country or a USD default.
            # Unknown currency keeps provider amounts, while USD fields remain null.
            settings = get_settings()
            currency_resolution = resolve_cached_customer_currency(db, provider=item.provider, customer_id=settings.google_ads_customer_id, override=item.provider_currency_code)
            currency = currency_resolution.currency_code
            item.provider_currency_code = currency
            usd = resolve_usd_metrics(db, provider_currency=currency, cpc=item.cpc, low_bid=item.low_bid, high_bid=item.high_bid, customer_id=settings.google_ads_customer_id)
            item.usd_cpc, item.usd_low_bid, item.usd_high_bid = usd.usd_cpc, usd.usd_low_bid, usd.usd_high_bid
            item.fx_rate, item.fx_rate_date, item.fx_source = usd.fx_rate, usd.fx_rate_date, usd.fx_source
            db.add(KeywordMetricEvidence(query_id=query.id, submitted_keyword=request.keyword, provider_keyword=item.provider_keyword or item.keyword, normalized_keyword=request.keyword.strip().casefold(), location_name=request.location_name, location_target=request.location_target or {}, language_code=request.language_code, country_code=request.country_code, provider=item.provider, source_kind=item.provider, avg_monthly_searches=item.avg_monthly_searches, competition=item.competition, competition_index=item.competition_index, cpc=item.cpc, low_bid=item.low_bid, high_bid=item.high_bid, provider_currency_code=item.provider_currency_code, usd_cpc=item.usd_cpc, usd_low_bid=item.usd_low_bid, usd_high_bid=item.usd_high_bid, fx_rate=item.fx_rate, fx_rate_date=item.fx_rate_date, fx_source=item.fx_source, monthly_history=item.monthly_history, raw_payload=item.raw or {}, cost=item.cost, mapping_status=result.mapping_status.get(request.keyword, "MAPPED")))
    if reservation:
        consumed = int(sum((row.operation_count or 0) for row in db.query(ProviderCall).filter(ProviderCall.stage == "keyword_metrics", ProviderCall.started_at >= batch.created_at).all()))
        finish(db, reservation, consumed)
    batch.returned_count=len(result.results) - result.unmapped_count; batch.mapped_count=batch.returned_count; batch.unmapped_count=result.unmapped_count; batch.status="COMPLETED"; batch.cost=0.0; db.commit()
    output=[]
    for k, v in result.results.items():
        derived = None
        if result.mapping_status.get(k) != "UNMAPPED":
            derived = calculate_derived_metrics(v.avg_monthly_searches, v.usd_cpc)
            evidence = db.query(KeywordMetricEvidence).filter_by(submitted_keyword=k, provider=v.provider).order_by(KeywordMetricEvidence.fetched_at.desc()).first()
            if evidence:
                stored = db.query(KeywordOpportunityMetrics).filter_by(keyword_metric_evidence_id=evidence.id, calculation_version=derived.calculation_version, ctr_model_version=derived.ctr_model_version).first()
                if stored is None:
                    stored = KeywordOpportunityMetrics(keyword_metric_evidence_id=evidence.id, commercial_search_value=derived.commercial_search_value, projected_metrics=derived.projected, ctr_model_version=derived.ctr_model_version, calculation_version=derived.calculation_version)
                    db.add(stored); db.flush()
                derived = type("StoredDerived", (), {"commercial_search_value": stored.commercial_search_value, "ctr_model_version": stored.ctr_model_version, "projected": stored.projected_metrics})()
        evidence_id = evidence.id if result.mapping_status.get(k) != "UNMAPPED" and evidence else None
        output.append(KeywordMetricResultOut(id=evidence_id, submitted_keyword=k, provider=v.provider, provider_keyword=v.provider_keyword or v.keyword, location_name=payload.target.location_name, location_target=payload.target.location_target, language_code=payload.target.language_code, country_code=payload.target.country_code, avg_monthly_searches=v.avg_monthly_searches, cpc=v.cpc, competition=v.competition, competition_index=v.competition_index, low_bid=v.low_bid, high_bid=v.high_bid, provider_currency_code=v.provider_currency_code, usd_cpc=v.usd_cpc, usd_low_bid=v.usd_low_bid, usd_high_bid=v.usd_high_bid, fx_rate=v.fx_rate, fx_rate_date=v.fx_rate_date, fx_source=v.fx_source, monthly_history=v.monthly_history, mapping_status=result.mapping_status.get(k,"MAPPED"), cost=v.cost, commercial_metrics=None if derived is None else {"commercial_search_value": derived.commercial_search_value, "ctr_model_version": derived.ctr_model_version, "projected": derived.projected}))
    db.commit()
    return KeywordMetricsResearchResponse(batch_id=batch.id, status=batch.status, provider=provider.provider_name, submitted_count=len(requests), mapped_count=len(result.results) - result.unmapped_count, unmapped_count=result.unmapped_count, provider_requests=result.provider_requests, results=output)


@router.get("/keyword-metrics")
def keyword_metrics_list(db: Session = Depends(get_db)):
    return [{"id": x.id, "keyword": x.submitted_keyword, "provider": x.provider, "status": x.mapping_status, "search_volume": x.avg_monthly_searches, "cost": x.cost, "fetched_at": x.fetched_at} for x in db.query(KeywordMetricEvidence).order_by(KeywordMetricEvidence.fetched_at.desc()).all()]


@router.get("/keyword-metrics/{evidence_id}")
def keyword_metrics_detail(evidence_id: str, db: Session = Depends(get_db)):
    item = db.get(KeywordMetricEvidence, evidence_id)
    if not item: raise HTTPException(404, "Keyword metric evidence not found")
    return item


@router.post("/keyword-metrics/refresh", response_model=KeywordMetricsResearchResponse)
async def keyword_metrics_refresh(payload: KeywordMetricsRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await keyword_metrics_research(payload, user, db)


@router.post("/keyword-metrics/research-batch")
async def keyword_metrics_research_batch(payload: KeywordMetricsBatchRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Resumable structured-location research; policy is calculated without transport."""
    if payload.provider != "google_ads":
        raise HTTPException(400, "research-batch requires explicit provider=google_ads")
    provider = keyword_metrics_provider(provider_name=payload.provider)
    batch = KeywordMetricBatch(provider=provider.provider_name, submitted_count=len(payload.keywords) * len(payload.locations), status="RUNNING")
    db.add(batch); db.flush()
    settings = get_settings()
    planned = (len(payload.keywords) + max(1, settings.keyword_metrics_max_batch_size) - 1) // max(1, settings.keyword_metrics_max_batch_size) * len(payload.locations)
    try:
        reservation = reserve(db, user.id, provider.provider_name, planned, batch.id, getattr(settings, "google_ads_daily_operation_budget", None), getattr(settings, "google_ads_customer_id", None))
    except ValueError as exc:
        db.rollback(); raise HTTPException(status_code=409, detail=str(exc)) from exc
    resolver = GoogleAdsGeoTargetResolver(
        client_factory=getattr(provider, "_client", None),
        enabled=settings.google_ads_enabled, live_approved=settings.google_ads_live_approved,
        credentials_configured=all((settings.google_ads_developer_token, settings.google_ads_client_id, settings.google_ads_client_secret, settings.google_ads_refresh_token, settings.google_ads_customer_id, settings.google_ads_login_customer_id)),
        freshness_days=settings.keyword_metrics_freshness_days)
    locations = [StructuredLocation(x.city, x.state_code, x.country_code) for x in payload.locations]
    from app.providers.google_ads_keyword_metrics import language_resource
    # FX transport is opt-in.  A missing PKR->USD rate must not silently
    # trigger an external FX request during keyword research.
    try:
        report = await MultiCityKeywordMetricsOrchestrator(db, provider, resolver, fx_provider=None, customer_id=settings.google_ads_customer_id, provider_currency_code=settings.google_ads_currency_code, minimum_sv=payload.minimum_sv or 260, freshness_days=settings.keyword_metrics_freshness_days).run(payload.keywords, locations, batch=batch)
    except Exception:
        finish(db, reservation, 0); db.commit(); raise
    finish(db, reservation, int(report.get("provider_requests", 0)))
    for row in report["results"]:
        evidence = db.get(KeywordMetricEvidence, row.get("evidence_id")) if row.get("evidence_id") else None
        if evidence:
            sv = evidence.avg_monthly_searches
            row["rank_rent_status"] = "MISSING_EVIDENCE" if sv is None else ("ELIGIBLE_FOR_RANK_RENT_PIPELINE" if payload.minimum_sv is None or sv >= payload.minimum_sv else "BELOW_SV_THRESHOLD")
    return {"batch_id": batch.id, "status": batch.status, "provider": provider.provider_name, "submitted_count": batch.submitted_count, **report}


@router.post("/keyword-metrics/send-to-validation", response_model=KeywordMetricsHandoffResponse)
def keyword_metrics_handoff(payload: KeywordMetricsHandoffRequest, db: Session = Depends(get_db)):
    handoffs=[]; existing_ids=[]; new_ids=[]; existing_handoff_ids=[]; new_handoff_ids=[]
    for evidence_id in dict.fromkeys(payload.evidence_ids):
        evidence=db.get(KeywordMetricEvidence, evidence_id)
        if not evidence: raise HTTPException(404, f"Keyword metric evidence not found: {evidence_id}")
        existing = db.query(KeywordMetricValidationHandoff).filter_by(evidence_id=evidence.id).order_by(KeywordMetricValidationHandoff.created_at.asc()).first()
        if existing:
            existing_ids.append(evidence.id)
            existing_handoff_ids.append(existing.id)
            handoffs.append(existing)
            continue
        handoff=KeywordMetricValidationHandoff(evidence_id=evidence.id, submitted_keyword=evidence.submitted_keyword, provider=evidence.provider, provider_keyword=evidence.provider_keyword, location_target=evidence.location_target, language_code=evidence.language_code, country_code=evidence.country_code, validation_profile_snapshot=payload.validation_profile.model_dump())
        db.add(handoff); db.flush(); handoffs.append(handoff); new_ids.append(evidence.id)
        new_handoff_ids.append(handoff.id)
    db.commit()
    return KeywordMetricsHandoffResponse(handoff_ids=[x.id for x in handoffs], evidence_ids=[x.evidence_id for x in handoffs], selected_count=len(handoffs), provider_requests=0, new_count=len(new_ids), existing_count=len(existing_ids), existing_evidence_ids=existing_ids, new_handoff_ids=new_handoff_ids, existing_handoff_ids=existing_handoff_ids, all_handoff_ids=[x.id for x in handoffs])

@router.get("/rank-rent/handoffs", response_model=list[KeywordMetricsHandoffOut])
def list_rank_rent_handoffs(db: Session = Depends(get_db)):
    rows = db.query(KeywordMetricValidationHandoff).order_by(KeywordMetricValidationHandoff.created_at.desc()).all()
    return [_handoff_out(row, db) for row in rows]

@router.get("/rank-rent/handoffs/{handoff_id}", response_model=KeywordMetricsHandoffOut)
def get_rank_rent_handoff(handoff_id: str, db: Session = Depends(get_db)):
    row = db.get(KeywordMetricValidationHandoff, handoff_id)
    if not row: raise HTTPException(404, "Rank & Rent handoff not found")
    return _handoff_out(row, db)

def _handoff_out(row: KeywordMetricValidationHandoff, db: Session):
    evidence = db.get(KeywordMetricEvidence, row.evidence_id)
    embedded = _local_city_matches(db, row.submitted_keyword)
    scope = resolve_scope(location_target=row.location_target, has_local_city_match=bool(embedded))
    needs_location = scope.scope == LOCAL_SCOPE and not (row.location_target or {}).get("city") and len(embedded) != 1
    return KeywordMetricsHandoffOut(handoff_id=row.id, evidence_id=row.evidence_id, keyword=row.submitted_keyword, search_volume=evidence.avg_monthly_searches if evidence else None, country_code=row.country_code, location_target=row.location_target or {}, language_code=row.language_code, provider=row.provider, provider_keyword=row.provider_keyword, validation_profile=row.validation_profile_snapshot or {}, created_at=row.created_at, status="PENDING", validation_scope=scope.scope, scope_reason=scope.reason, location_status="NEEDS_CONFIRMATION" if needs_location else ("NOT_REQUIRED" if scope.scope == GENERAL_SCOPE else "RESOLVED"), population_applicability="NOT_APPLICABLE" if scope.scope == GENERAL_SCOPE else "APPLICABLE", serp_mode="NATIONAL" if scope.scope == GENERAL_SCOPE else "LOCALIZED", readiness_status="NEEDS_LOCATION" if needs_location else "CLASSIFIED")


@router.post("/runs/{run_id}/proxy-authority")
async def evaluate_proxy_run_endpoint(run_id: str, payload: dict | None = None, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run: raise HTTPException(404, "Run not found")
    payload = payload or {}
    candidates = db.query(RunCandidate).filter_by(run_id=run_id).all()
    selected = set(payload.get("run_candidate_ids") or [item.id for item in candidates])
    results = []
    from app.models.entities import SerpResultRow
    for rc in candidates:
        if rc.id not in selected or not rc.serp_snapshot_id: continue
        rows = db.query(SerpResultRow).filter_by(snapshot_id=rc.serp_snapshot_id).order_by(SerpResultRow.position).all()
        decision = await evaluate_run_candidate_proxy(db, run, rc, rows, float(payload.get("threshold", 14.0)), int(payload.get("minimum_weak", 4)), int(payload.get("ideal_weak", 5)), bool(payload.get("force_refresh", False)))
        results.append({"run_candidate_id": rc.id, "classification": decision.classification, "reason": decision.reason, "uncertainty": decision.uncertainty, "recommended_action": decision.recommended_action, "why_not_rejected": decision.why_not_rejected, "evidence": rc.proxy_result})
    return {"run_id": run_id, "provider": "ahrefs", "metric": "domain_rating", "calibration_state": "UNCALIBRATED_HIGH_RECALL", "attribution": "Domain Rating by Ahrefs", "results": results}


@router.post("/projects/{project_id}/imports/niches")
async def import_niches_endpoint(project_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not db.get(Project, project_id): raise HTTPException(404, "Project not found")
    return import_niches(db, project_id, await file.read(), file.filename or "niches.csv")


@router.post("/projects/{project_id}/imports/keywords-everywhere")
async def import_ke_endpoint(project_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not db.get(Project, project_id): raise HTTPException(404, "Project not found")
    return import_keyword_export(db, project_id, await file.read(), "keywords_everywhere_csv", file.filename or "keywords-everywhere.csv")


@router.post("/projects/{project_id}/imports/ahrefs")
async def import_ahrefs_endpoint(project_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not db.get(Project, project_id): raise HTTPException(404, "Project not found")
    return import_keyword_export(db, project_id, await file.read(), "ahrefs_csv", file.filename or "ahrefs.csv")


@router.post("/projects/{project_id}/imports/cities")
async def import_cities_endpoint(project_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not db.get(Project, project_id): raise HTTPException(404, "Project not found")
    return import_cities(db, await file.read(), file.filename or "cities.csv", project_id)


@router.get("/runs/{run_id}/export")
def export_run_endpoint(run_id: str, db: Session = Depends(get_db)):
    if not db.get(Run, run_id): raise HTTPException(404, "Run not found")
    return Response(export_run_csv(db, run_id), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=run-{run_id}.csv"})


@router.get("/projects/{project_id}/export")
def export_project_endpoint(project_id: str, db: Session = Depends(get_db)):
    if not db.get(Project, project_id): raise HTTPException(404, "Project not found")
    return Response(export_project_csv(db, project_id), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=project-{project_id}.csv"})


@router.get("/project-candidates/{project_candidate_id}/history/export")
def export_history_endpoint(project_candidate_id: str, db: Session = Depends(get_db)):
    return Response(export_candidate_history_csv(db, project_candidate_id), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=history-{project_candidate_id}.csv"})


@router.post("/projects/{project_id}/imports/moz")
async def import_moz_endpoint(project_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not db.get(Project, project_id): raise HTTPException(404, "Project not found")
    return import_moz(db, project_id, await file.read(), file.filename or "moz.csv")


@router.post("/projects/{project_id}/imports/manual-moz")
async def import_manual_moz_endpoint(project_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not db.get(Project, project_id): raise HTTPException(404, "Project not found")
    return import_manual_moz_csv(db, project_id, await file.read(), file.filename or "manual-moz.csv")


@router.post("/projects/{project_id}/imports/manual")
def import_manual_endpoint(project_id: str, payload: dict, db: Session = Depends(get_db)):
    if not db.get(Project, project_id): raise HTTPException(404, "Project not found")
    return import_manual_evidence(db, project_id, payload)


@router.get("/imports/{import_batch_id}")
def import_batch_detail(import_batch_id: str, db: Session = Depends(get_db)):
    batch = db.get(ImportBatch, import_batch_id)
    if not batch: raise HTTPException(404, "Import batch not found")
    return {"id": batch.id, "project_id": batch.project_id, "source_kind": batch.source_kind, "provider": batch.provider, "file_name": batch.file_name, "file_hash": batch.file_hash, "row_count": batch.row_count, "accepted": batch.accepted_count, "rejected": batch.rejected_count, "errors": batch.error_summary}


@router.get("/imports/{import_batch_id}/errors")
def import_batch_errors(import_batch_id: str, db: Session = Depends(get_db)):
    batch = db.get(ImportBatch, import_batch_id)
    if not batch: raise HTTPException(404, "Import batch not found")
    return {"import_batch_id": batch.id, "errors": batch.error_summary or {}}


def _local_city_matches(db: Session, keyword: str):
    normalized_keyword = normalize_keyword(keyword)
    cache = db.info.setdefault("city_match_cache", {})
    if normalized_keyword in cache:
        return cache[normalized_keyword]
    tokens = [token for token in normalized_keyword.split() if len(token) >= 3]
    candidate_rows = db.scalars(select(City).where(or_(*[City.name.ilike(f"%{token}%") for token in tokens]))).all() if tokens else []
    cities = candidate_rows
    with_state = [city for city in cities
                  if re.search(rf"\b{re.escape(normalize_keyword(city.name))}\b", normalized_keyword)
                  and re.search(rf"\b{re.escape(city.state_code.casefold())}\b", normalized_keyword)]
    result = with_state or [city for city in cities if re.search(rf"\b{re.escape(normalize_keyword(city.name))}\b", normalized_keyword)]
    cache[normalized_keyword] = result
    return result


def _attach_handoffs(db: Session, project: Project, handoff_ids: list[str], location_overrides: dict[str, dict] | None = None):
    created = 0; existing = 0; ids = []
    ambiguities = []
    location_overrides = location_overrides or {}
    for handoff_id in handoff_ids:
        handoff = db.get(KeywordMetricValidationHandoff, handoff_id)
        if not handoff:
            raise HTTPException(404, "Search Volume handoff not found")
        evidence = db.get(KeywordMetricEvidence, handoff.evidence_id)
        target = {**(handoff.location_target or {}), **location_overrides.get(handoff_id, {})}
        city_name = target.get("city") or target.get("city_name")
        state_code = target.get("state_code") or target.get("state")
        embedded = _local_city_matches(db, handoff.submitted_keyword)
        scope = resolve_scope(location_target=target, has_local_city_match=bool(embedded))
        if scope.scope == GENERAL_SCOPE:
            geographic_id = target.get("country_code") or handoff.country_code or "US"
            canonical = canonical_identity(handoff.submitted_keyword, str(geographic_id), handoff.language_code, handoff.country_code)
            entity = db.scalar(select(CandidateEntity).where(CandidateEntity.identity_key == identity_key(canonical)))
            if not entity:
                entity = CandidateEntity(canonical_identity=canonical, identity_key=identity_key(canonical), service_term_normalized=normalize_keyword(handoff.submitted_keyword), city_id=None, validation_scope=GENERAL_SCOPE, language_code=handoff.language_code, country_code=handoff.country_code, canonical_keyword=handoff.submitted_keyword)
                db.add(entity); db.flush()
            candidate = db.scalar(select(ProjectCandidate).where(ProjectCandidate.project_id == project.id, ProjectCandidate.candidate_entity_id == entity.id))
            if candidate and candidate.search_volume_evidence_id and candidate.search_volume_evidence_id != handoff.evidence_id:
                raise HTTPException(409, "PROJECT_CANDIDATE_EVIDENCE_CONFLICT")
            if not candidate:
                candidate = ProjectCandidate(project_id=project.id, candidate_entity_id=entity.id, validation_scope=GENERAL_SCOPE, scope_reason=scope.reason, search_volume_evidence_id=handoff.evidence_id, original_input=handoff.submitted_keyword, display_keyword=handoff.submitted_keyword, current_status="IMPORTED", current_reason_codes=["SEARCH_VOLUME_HANDOFF", "GENERAL_NICHE"], broad_category="General niche")
                db.add(candidate); db.flush(); created += 1
            else:
                candidate.validation_scope = GENERAL_SCOPE
                candidate.scope_reason = scope.reason
                if candidate.search_volume_evidence_id is None: candidate.search_volume_evidence_id = handoff.evidence_id
                existing += 1
            ids.append(candidate.id)
            continue
        if not city_name or not state_code:
            # Country-targeted Search Volume research can still contain an
            # explicitly localized keyword. Reuse the local population
            # registry only when the embedded city is unambiguous; never
            # guess a state or call a provider during handoff.
            if len(embedded) == 1:
                city_name = embedded[0].name
                state_code = embedded[0].state_code
            elif len(embedded) > 1:
                ambiguities.append({"handoff_id": handoff.id, "keyword": handoff.submitted_keyword, "candidates": [{"city": city.name, "state": city.state_code, "city_id": city.id} for city in embedded]})
                continue
        if not city_name or not state_code:
            possible = _local_city_matches(db, handoff.submitted_keyword)
            if possible:
                raise HTTPException(422, {"code": "HANDOFF_CITY_AMBIGUOUS", "message": "Location needs confirmation before Rank & Rent validation.", "ambiguities": [{"handoff_id": handoff.id, "keyword": handoff.submitted_keyword, "candidates": [{"city": c.name, "state": c.state_code, "city_id": c.id} for c in possible]}], "candidates": [{"city": c.name, "state": c.state_code, "city_id": c.id} for c in possible]})
            raise HTTPException(422, {"code": "HANDOFF_CITY_UNRESOLVED", "message": "Location needs confirmation before Rank & Rent validation.", "keyword": handoff.submitted_keyword, "candidates": []})
        city = db.scalar(select(City).where(City.name.ilike(city_name), City.state_code == state_code.upper()))
        if not city:
            raise HTTPException(422, {"code": "HANDOFF_CITY_UNRESOLVED", "message": "The selected city is not available in the local population registry.", "keyword": handoff.submitted_keyword, "candidates": []})
        geographic_id = str((target.get("geo_target_ids") or [f"{city.name},{city.state_code}"])[0])
        canonical = canonical_identity(handoff.submitted_keyword, geographic_id, handoff.language_code, handoff.country_code)
        entity = db.scalar(select(CandidateEntity).where(CandidateEntity.identity_key == identity_key(canonical)))
        if not entity:
            entity = CandidateEntity(canonical_identity=canonical, identity_key=identity_key(canonical), service_term_normalized=normalize_keyword(handoff.submitted_keyword), city_id=city.id, validation_scope=LOCAL_SCOPE, language_code=handoff.language_code, country_code=handoff.country_code, canonical_keyword=handoff.submitted_keyword)
            db.add(entity); db.flush()
        candidate = db.scalar(select(ProjectCandidate).where(ProjectCandidate.project_id == project.id, ProjectCandidate.candidate_entity_id == entity.id))
        if candidate and candidate.search_volume_evidence_id and candidate.search_volume_evidence_id != handoff.evidence_id:
            raise HTTPException(409, "PROJECT_CANDIDATE_EVIDENCE_CONFLICT")
        if not candidate:
            candidate = ProjectCandidate(project_id=project.id, candidate_entity_id=entity.id, validation_scope=LOCAL_SCOPE, scope_reason=scope.reason, search_volume_evidence_id=handoff.evidence_id, original_input=handoff.submitted_keyword, display_keyword=handoff.submitted_keyword, current_status="IMPORTED", current_reason_codes=["SEARCH_VOLUME_HANDOFF"], broad_category="Search Volume handoff")
            db.add(candidate); db.flush(); created += 1
        else:
            if candidate.search_volume_evidence_id is None: candidate.search_volume_evidence_id = handoff.evidence_id
            existing += 1
        ids.append(candidate.id)
    if ambiguities:
        raise HTTPException(409, {"code": "HANDOFF_CITY_AMBIGUOUS", "message": "One or more locations need confirmation before Rank & Rent validation.", "ambiguities": ambiguities, "candidates": ambiguities[0]["candidates"] if len(ambiguities) == 1 else []})
    return created, existing, ids


@router.post("/projects/{project_id}/handoffs/attach", response_model=ProjectHandoffAttachResponse)
def attach_project_handoffs(project_id: str, payload: ProjectHandoffAttachRequest, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project: raise HTTPException(404, "Project not found")
    pending = []
    ready_ids = []
    for handoff_id in dict.fromkeys(payload.handoff_ids):
        handoff = db.get(KeywordMetricValidationHandoff, handoff_id)
        if not handoff: raise HTTPException(404, "Search Volume handoff not found")
        target = {**(handoff.location_target or {}), **payload.location_overrides.get(handoff_id, {})}
        embedded = _local_city_matches(db, handoff.submitted_keyword)
        scope = resolve_scope(location_target=target, has_local_city_match=bool(embedded))
        if scope.scope == LOCAL_SCOPE and not (target.get("city") or target.get("city_name") or target.get("state_code") or target.get("state")) and len(embedded) != 1:
            if embedded:
                pending.append({"handoff_id": handoff.id, "status": "LOCAL_LOCATION_REQUIRED", "validation_scope": LOCAL_SCOPE, "keyword": handoff.submitted_keyword, "city_candidates": [{"city": c.name, "state": c.state_code, "city_id": c.id} for c in embedded]})
                continue
        ready_ids.append(handoff_id)
    created, existing, ids = _attach_handoffs(db, project, ready_ids, payload.location_overrides) if ready_ids else (0, 0, [])
    db.commit()
    ready_results = [{"handoff_id": h.id, "status": "GENERAL_READY" if db.get(ProjectCandidate, cid).validation_scope == GENERAL_SCOPE else "LOCAL_READY", "validation_scope": db.get(ProjectCandidate, cid).validation_scope, "project_candidate_id": cid, "keyword": db.get(ProjectCandidate, cid).display_keyword} for h, cid in zip([db.get(KeywordMetricValidationHandoff, hid) for hid in ready_ids], ids)]
    results = pending + ready_results
    return ProjectHandoffAttachResponse(project_id=project_id, created_count=created, existing_count=existing, project_candidate_ids=ids, results=results, summary={"total": len(results), "ready": len(ready_results), "needs_location": len(pending), "failed": 0})


@router.post("/projects")
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    p = Project(name=payload.name, description=payload.description, profile_snapshot=payload.profile.model_dump())
    db.add(p); db.flush()
    candidate_ids = []
    for handoff_id in payload.handoff_ids:
        handoff = db.get(KeywordMetricValidationHandoff, handoff_id)
        if not handoff:
            raise HTTPException(404, "Search Volume handoff not found")
        evidence = db.get(KeywordMetricEvidence, handoff.evidence_id)
        target = handoff.location_target or {}
        city_name = target.get("city") or target.get("city_name")
        state_code = target.get("state_code") or target.get("state")
        if not city_name or not state_code:
            raise HTTPException(422, "Rank & Rent candidates require a city-targeted Search Volume handoff")
        city = db.scalar(select(City).where(City.name.ilike(city_name), City.state_code == state_code.upper()))
        if not city:
            raise HTTPException(422, "The handoff city is not available in the local population registry")
        geographic_id = str((target.get("geo_target_ids") or [f"{city.name},{city.state_code}"])[0])
        canonical = canonical_identity(handoff.submitted_keyword, geographic_id, handoff.language_code, handoff.country_code)
        entity = db.scalar(select(CandidateEntity).where(CandidateEntity.identity_key == identity_key(canonical)))
        if not entity:
            entity = CandidateEntity(canonical_identity=canonical, identity_key=identity_key(canonical), service_term_normalized=normalize_keyword(handoff.submitted_keyword), city_id=city.id, language_code=handoff.language_code, country_code=handoff.country_code, canonical_keyword=handoff.submitted_keyword)
            db.add(entity); db.flush()
        candidate = db.scalar(select(ProjectCandidate).where(ProjectCandidate.project_id == p.id, ProjectCandidate.candidate_entity_id == entity.id))
        if candidate and candidate.search_volume_evidence_id and candidate.search_volume_evidence_id != handoff.evidence_id:
            raise HTTPException(409, "Project candidate already references different Search Volume evidence")
        if not candidate:
            candidate = ProjectCandidate(project_id=p.id, candidate_entity_id=entity.id, search_volume_evidence_id=handoff.evidence_id, original_input=handoff.submitted_keyword, display_keyword=handoff.submitted_keyword, current_status="IMPORTED", current_reason_codes=["SEARCH_VOLUME_HANDOFF"], broad_category="Search Volume handoff")
            db.add(candidate); db.flush()
        elif candidate.search_volume_evidence_id is None:
            candidate.search_volume_evidence_id = handoff.evidence_id
        candidate_ids.append(candidate.id)
    db.commit(); db.refresh(p)
    return {"id": p.id, "name": p.name, "profile": p.profile_snapshot, "candidate_ids": candidate_ids, "candidate_count": len(candidate_ids)}


@router.post("/cities")
def add_city(name: str, state_code: str, population: int, vintage: str = "manual", db: Session = Depends(get_db)):
    c = City(name=name.strip(), state_code=state_code.upper(), population=population, population_vintage=vintage)
    db.add(c); db.commit(); db.refresh(c)
    return {"id": c.id, "name": c.name, "state": c.state_code, "population": c.population}


@router.get("/cities")
def list_cities(min_population: int = 20000, max_population: int = 120000, db: Session = Depends(get_db)):
    rows = db.scalars(select(City).where(City.population >= min_population, City.population <= max_population).order_by(City.state_code, City.name)).all()
    return [{"id": c.id, "name": c.name, "state": c.state_code, "population": c.population} for c in rows]


@router.post("/projects/{project_id}/candidates/generate")
def generate_candidates(project_id: str, payload: CandidateGenerateRequest, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    profile = payload.profile or ValidationProfile(**project.profile_snapshot)
    stmt = select(City).where(City.population >= profile.min_population, City.population <= profile.max_population)
    if payload.state_codes:
        stmt = stmt.where(City.state_code.in_([x.upper() for x in payload.state_codes]))
    cities = db.scalars(stmt).all()
    created = 0
    for niche in payload.niches:
        for city in cities:
            if not population_gate(city.population, profile).passed:
                continue
            kw = build_keyword(niche.service_term, city.name, city.state_code)
            existing = db.scalar(select(Candidate).where(Candidate.project_id == project_id, Candidate.normalized_keyword == kw))
            if existing:
                continue
            db.add(Candidate(
                project_id=project_id, city_id=city.id, broad_category=niche.broad_category,
                micro_niche=niche.micro_niche, service_term=normalize_keyword(niche.service_term),
                normalized_keyword=kw, display_keyword=kw,
            ))
            created += 1
    db.commit()
    return {"created": created, "eligible_cities": len(cities)}


@router.get("/projects/{project_id}/candidates", response_model=list[CandidateOut])
def candidates(project_id: str, db: Session = Depends(get_db)):
    rows = db.scalars(select(Candidate).where(Candidate.project_id == project_id).order_by(Candidate.display_keyword)).all()
    return [CandidateOut(
        id=c.id, keyword=c.display_keyword, city=c.city.name if c.city else None,
        state=c.city.state_code if c.city else None, population=c.city.population if c.city else None,
        search_volume=c.search_volume, cpc=c.cpc, low_da_count=c.low_da_count,
        status=c.status, automatic_pass=c.automatic_pass, reason_codes=c.reason_codes or []
    ) for c in rows]


@router.post("/projects/{project_id}/run")
async def run_project(project_id: str, payload: RunRequest, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    profile = payload.profile or ValidationProfile(**project.profile_snapshot)
    stmt = select(Candidate).where(Candidate.project_id == project_id)
    if payload.candidate_ids:
        stmt = stmt.where(Candidate.id.in_(payload.candidate_ids))
    rows = db.scalars(stmt).all()
    processed = []
    # Synchronous MVP only. Replace with queued work in Phase 1B.
    for c in rows:
        processed.append(await process_candidate(db, c, profile))
    return {
        "processed": len(processed),
        "passes_primary": sum(1 for x in processed if x.automatic_pass is True),
        "rejected": sum(1 for x in processed if x.automatic_pass is False),
    }


@router.post("/projects/{project_id}/runs", response_model=RunOut)
def create_run(project_id: str, payload: RunCreate, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    profile = payload.profile or ValidationProfile(**project.profile_snapshot)
    selected_ids = payload.candidate_ids
    if selected_ids is None:
        selected_ids = [pc.id for pc in db.scalars(select(ProjectCandidate).where(ProjectCandidate.project_id == project_id)).all()]
    valid_ids = {pc.id for pc in db.scalars(select(ProjectCandidate).where(ProjectCandidate.project_id == project_id, ProjectCandidate.id.in_(selected_ids))).all()}
    if set(selected_ids) != valid_ids:
        raise HTTPException(422, "One or more selected candidates do not belong to this project")
    configuration = profile.model_dump()
    configuration["selected_project_candidate_ids"] = list(dict.fromkeys(selected_ids))
    run = Run(project_id=project_id, min_population=profile.min_population, max_population=profile.max_population,
              min_search_volume=profile.min_search_volume, da_threshold=profile.da_threshold,
              required_low_da_count=profile.minimum_weak_domains, minimum_weak_domains=profile.minimum_weak_domains,
              ideal_weak_domains=profile.ideal_weak_domains, authority_evaluation_mode=profile.authority_evaluation_mode,
              authority_batch_size=profile.authority_batch_size, adaptive_seek_ideal=profile.adaptive_seek_ideal, organic_depth=profile.organic_depth,
              kd_enabled=profile.kd_enabled, kd_provider=profile.kd_provider, kd_threshold=profile.kd_threshold, kd_operator=profile.kd_operator, kd_mode=profile.kd_mode,
              country_code="US", language_code="en", configuration_snapshot=configuration,
              provider_snapshot={}, freshness_policy_snapshot={}, enabled_gates={"population": True, "search_volume": True, "authority": True})
    db.add(run); db.commit(); db.refresh(run)
    return run


def _run_response(db: Session, run: Run):
    rows = db.scalars(select(RunCandidate).where(RunCandidate.run_id == run.id)).all()
    terminal = {"PASS", "PRIMARY_REJECTED", "SV_REJECTED", "POPULATION_REJECTED", "ERROR_RETRYABLE", "ERROR_TERMINAL"}
    processed = sum(1 for row in rows if row.finished_at or row.status in terminal)
    progress = 100 if run.status == "COMPLETED" else (round(processed / len(rows) * 100) if rows else 0)
    results = []
    for row in rows:
        pc = db.get(ProjectCandidate, row.project_candidate_id)
        # Canonical handoff evidence lives on RunCandidate; retain legacy
        # fallbacks for historical rows.
        if row.keyword_metric_evidence_id:
            sv = db.get(KeywordMetricEvidence, row.keyword_metric_evidence_id)
        elif pc and pc.search_volume_evidence_id:
            sv = db.get(KeywordMetricEvidence, pc.search_volume_evidence_id)
        elif row.search_volume_evidence_id:
            sv = db.get(SearchVolumeEvidence, row.search_volume_evidence_id)
        else:
            sv = None
        # The status projection below is legacy-field based; mirror the
        # selected canonical evidence in memory so handoff runs are reported
        # as PASS without changing persisted lineage.
        if sv and not row.search_volume_evidence_id:
            row.search_volume_evidence_id = sv.id
        snap = db.get(SerpSnapshot, row.serp_snapshot_id) if row.serp_snapshot_id else None
        serp_rows = db.scalars(select(SerpResultRow).where(SerpResultRow.snapshot_id == snap.id).order_by(SerpResultRow.position)).all() if snap else []
        authority = []
        da_links = {link.serp_result_row_id: link for link in db.scalars(select(RunCandidateAuthorityEvidence).where(RunCandidateAuthorityEvidence.run_candidate_id == row.id)).all()}
        for result in serp_rows:
            link = da_links.get(result.id)
            ev = db.get(AuthorityEvidence, link.authority_evidence_id) if link else None
            proxy_link = db.scalar(select(RunCandidateProxyAuthorityEvidence).where(RunCandidateProxyAuthorityEvidence.run_candidate_id == row.id, RunCandidateProxyAuthorityEvidence.serp_result_row_id == result.id))
            proxy = db.get(ProxyAuthorityEvidence, proxy_link.proxy_authority_evidence_id) if proxy_link else None
            backlink_link = db.scalar(select(RunCandidateBacklinkEvidence).where(RunCandidateBacklinkEvidence.run_candidate_id == row.id, RunCandidateBacklinkEvidence.serp_result_row_id == result.id))
            backlink = db.get(ProxyBacklinkFeatureEvidence, backlink_link.proxy_backlink_evidence_id) if backlink_link else None
            authority.append({"position": result.position, "domain": result.root_domain, "url": result.url, "da": link.da_value_used if link else None, "pa": ev.pa if ev else None, "provider": ev.provider if ev else None, "ahrefs_dr": proxy.domain_rating if proxy else None, "da_provider": ev.provider if ev else None, "dr_provider": proxy.provider if proxy else None, "referring_domains": backlink.referring_domains if backlink else None, "referring_main_domains": backlink.referring_main_domains if backlink else None, "referring_ips": backlink.referring_ips if backlink else None, "referring_subnets": backlink.referring_subnets if backlink else None, "backlinks": backlink.backlinks if backlink else None, "backlinks_spam_score": backlink.backlinks_spam_score if backlink else None, "backlink_provider": backlink.provider if backlink else None})
        serp_reason = "SERP_PROVIDER_REQUEST_ERROR" if "SERP_PROVIDER_REQUEST_ERROR" in (row.reason_codes or []) else ("SERP_INSUFFICIENT_ORGANIC_RESULTS" if "SERP_INSUFFICIENT_ORGANIC_RESULTS" in (row.reason_codes or []) else None)
        serp_status = "RETRYABLE" if serp_reason else ("PASS" if row.serp_snapshot_id and row.status not in {"ERROR_RETRYABLE"} else "NOT RUN")
        results.append({"run_candidate_id": row.id, "project_candidate_id": row.project_candidate_id, "keyword": pc.display_keyword if pc else None, "validation_scope": row.validation_scope or (pc.validation_scope if pc else "LOCAL_RANK_RENT"), "population_applicability": "NOT_APPLICABLE" if row.validation_scope == "GENERAL_NICHE" else ("PASS" if row.population_evidence_id and row.status != "POPULATION_REJECTED" else ("REJECTED" if row.status == "POPULATION_REJECTED" else "NOT RUN")), "serp_mode": "NATIONAL" if row.validation_scope == "GENERAL_NICHE" else "LOCAL_CITY", "status": row.status, "reason_codes": row.reason_codes or [], "population": "NOT APPLICABLE" if row.validation_scope == "GENERAL_NICHE" else ("PASS" if row.population_evidence_id and row.status != "POPULATION_REJECTED" else ("REJECTED" if row.status == "POPULATION_REJECTED" else "NOT RUN")), "search_volume": "PASS" if row.search_volume_evidence_id and row.status not in {"SV_REJECTED", "POPULATION_REJECTED"} else ("REJECTED" if row.status == "SV_REJECTED" else "NOT RUN"), "search_volume_value": sv.avg_monthly_searches if sv else None, "search_volume_provider": sv.provider if sv else None, "serp": serp_status, "serp_reason": serp_reason, "serp_count": len(serp_rows), "serp_required": run.organic_depth, "serp_evidence": [{"position": item.position, "domain": item.root_domain, "url": item.url, "title": item.title} for item in serp_rows], "authority_opportunity": row.opportunity_classification if row.validation_scope == "GENERAL_NICHE" else None, "authority_opportunity_reason": row.authority_opportunity_reason, "weak_site_count": row.low_da_count, "authority_threshold": row.da_threshold_used, "da": "NOT RUN" if row.authority_results_available is None else ("PASS" if row.primary_gate_passed else "REJECTED"), "da_evidence": authority, "deep_analysis": "NOT RUN" if row.authority_results_available is None else ("NOT RUN" if row.validation_scope == "GENERAL_NICHE" and row.opportunity_classification is None else ("PASS" if row.opportunity_classification in {"PASS", "IDEAL", "STRONG_POTENTIAL", "GOOD_POTENTIAL", "POTENTIAL_NICHE"} else "FAIL")), "kd": "NOT RUN" if row.kd_status in (None, "MISSING") else row.kd_status, "final_result": "NOT PRODUCED" if row.status == "ERROR_RETRYABLE" else row.status})
    return {**{column.name: getattr(run, column.name) for column in Run.__table__.columns}, "progress": progress, "candidate_results": results}


@router.get("/runs/{run_id}", response_model=RunOut)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return _run_response(db, run)


@router.post("/runs/{run_id}/execute", response_model=RunOut)
async def execute_run_endpoint(run_id: str, payload: RunCreate | None = None, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    ids = payload.candidate_ids if payload and payload.candidate_ids is not None else (run.configuration_snapshot or {}).get("selected_project_candidate_ids")
    try:
        return _run_response(db, await execute_run(db, run_id, ids))
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/projects/{project_id}/recalculate/preview")
def recalculate_preview(project_id: str, payload: RunCreate, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    profile = payload.profile or ValidationProfile(**project.profile_snapshot)
    return preview_recalculation(db, project_id, profile, payload.candidate_ids)

@router.post("/projects/{project_id}/validation-preview")
def validation_preview(project_id: str, payload: RunCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Zero-network UI-4 preflight; downstream work stays conditional on fail-fast gates."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    profile = payload.profile or ValidationProfile(**project.profile_snapshot)
    preview = preview_recalculation(db, project_id, profile, payload.candidate_ids)
    return {
        "project_id": project_id,
        "project_name": project.name,
        "candidate_ids": payload.candidate_ids,
        "profile": profile.model_dump(),
        "population_policy": {"enabled": profile.population_enabled, "minimum": profile.min_population, "maximum": profile.max_population},
        "search_volume_policy": {"enabled": profile.search_volume_enabled, "minimum": profile.min_search_volume},
        "authority_policy": {"threshold": profile.da_threshold, "required_weak": profile.required_low_da_count, "ideal_weak": profile.ideal_weak_domains, "depth": profile.organic_depth},
        "kd_policy": {"enabled": profile.kd_enabled, "provider": profile.kd_provider, "threshold": profile.kd_threshold, "mode": profile.kd_mode},
        "candidate_count": preview["total_affected"],
        "evidence": preview["reusable_evidence_by_stage"],
        "fresh_work": preview["estimated_provider_calls_by_stage"],
        "conditional_work": {"serp": "CONDITIONAL_ON_POPULATION_AND_SV", "authority": "CONDITIONAL_ON_SERP", "kd": "CONDITIONAL_ON_DA_QUALIFICATION"},
        "estimated_provider_calls": preview["estimated_provider_calls"],
        "estimated_cost": preview["estimated_cost"],
        "transport_would_occur": False,
        "preview_network_requests": 0,
    }


@router.post("/projects/{project_id}/recalculate", response_model=RunOut)
async def recalculate_project(project_id: str, payload: RunCreate, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    profile = payload.profile or ValidationProfile(**project.profile_snapshot)
    return await recalculate(db, project_id, profile, candidate_ids=payload.candidate_ids)


@router.get("/projects/{project_id}/ledger")
def project_ledger(project_id: str, page: int = 1, page_size: int = 50, status: str | None = None,
                  broad_category: str | None = None, micro_niche: str | None = None,
                  nano_niche: str | None = None, state: str | None = None,
                  min_population: int | None = None, max_population: int | None = None,
                  min_sv: int | None = None, max_sv: int | None = None,
                  min_kd: float | None = None, max_kd: float | None = None,
                  kd_provider: str | None = None, kd_status: str | None = None,
                  min_low_da: int | None = None, primary_result: str | None = None,
                  reason_code: str | None = None, db: Session = Depends(get_db)):
    return ledger(db, project_id, page, min(page_size, 200), status, broad_category, micro_niche, nano_niche, state,
                  min_population, max_population, min_sv, max_sv, min_kd, max_kd, kd_provider, kd_status,
                  min_low_da, primary_result, reason_code)


@router.get("/project-candidates/{project_candidate_id}/history")
def project_candidate_history(project_candidate_id: str, db: Session = Depends(get_db)):
    return candidate_history(db, project_candidate_id)


@router.post("/overlay/metrics")
async def overlay_metrics(payload: OverlayRequest):
    targets = [AuthorityTarget(url=u, root_domain=root_domain(u)) for u in payload.urls]
    provider = authority_provider()
    metrics = await provider.fetch(targets)
    return {
        "by_url": {
            m.url: {
                "root_domain": m.root_domain, "da": m.da, "pa": m.pa,
                "spam_score": m.spam_score, "linking_root_domains": m.linking_root_domains,
                "backlinks": m.backlinks, "provider": m.provider,
            } for m in metrics
        }
    }
