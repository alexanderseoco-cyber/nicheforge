from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.models.entities import ImportBatch, Project, City, Candidate, Run
from app.schemas.domain import ProjectCreate, CandidateGenerateRequest, CandidateOut, RunRequest, RunCreate, RunOut, ValidationProfile, OverlayRequest
from app.services.normalization import normalize_keyword, build_keyword
from app.services.gates import population_gate
from app.services.pipeline import process_candidate
from app.providers.factory import authority_provider
from app.providers.contracts import AuthorityTarget
from app.services.normalization import root_domain
from app.services.run_pipeline import execute_run
from app.services.recalculation import preview_recalculation, recalculate, ledger, candidate_history
from app.services.imports import export_candidate_history_csv, export_project_csv, export_run_csv, import_cities, import_keyword_export, import_manual_evidence, import_moz, import_niches

router = APIRouter(prefix="/api/v1")


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


@router.post("/projects")
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    p = Project(name=payload.name, description=payload.description, profile_snapshot=payload.profile.model_dump())
    db.add(p); db.commit(); db.refresh(p)
    return {"id": p.id, "name": p.name, "profile": p.profile_snapshot}


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
    run = Run(project_id=project_id, min_population=profile.min_population, max_population=profile.max_population,
              min_search_volume=profile.min_search_volume, da_threshold=profile.da_threshold,
              required_low_da_count=profile.minimum_weak_domains, minimum_weak_domains=profile.minimum_weak_domains,
              ideal_weak_domains=profile.ideal_weak_domains, authority_evaluation_mode=profile.authority_evaluation_mode,
              authority_batch_size=profile.authority_batch_size, organic_depth=profile.organic_depth,
              kd_enabled=profile.kd_enabled, kd_provider=profile.kd_provider, kd_threshold=profile.kd_threshold, kd_operator=profile.kd_operator, kd_mode=profile.kd_mode,
              country_code="US", language_code="en", configuration_snapshot=profile.model_dump(),
              provider_snapshot={}, freshness_policy_snapshot={}, enabled_gates={"population": True, "search_volume": True, "authority": True})
    db.add(run); db.commit(); db.refresh(run)
    return run


@router.get("/runs/{run_id}", response_model=RunOut)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return run


@router.post("/runs/{run_id}/execute", response_model=RunOut)
async def execute_run_endpoint(run_id: str, payload: RunCreate | None = None, db: Session = Depends(get_db)):
    ids = payload.candidate_ids if payload else None
    try:
        return await execute_run(db, run_id, ids)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/projects/{project_id}/recalculate/preview")
def recalculate_preview(project_id: str, payload: RunCreate, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    profile = payload.profile or ValidationProfile(**project.profile_snapshot)
    return preview_recalculation(db, project_id, profile, payload.candidate_ids)


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
