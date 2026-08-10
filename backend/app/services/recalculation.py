from __future__ import annotations

from sqlalchemy import func, select

from app.models.entities import AuthorityEvidence, CandidateEntity, CandidateEvent, City, KeywordDifficultyEvidence, ProjectCandidate, Run, RunCandidate, RunCandidateAuthorityEvidence, SearchVolumeEvidence, PopulationEvidence, SerpResultRow, SerpSnapshot
from app.schemas.domain import ValidationProfile
from app.services.run_pipeline import execute_run
from app.services.authority_evaluation import AuthorityEvaluationMode, evaluate_authority
from app.domain.freshness import FreshnessPolicy
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _profile_from_run(run: Run) -> ValidationProfile:
    return ValidationProfile(min_population=run.min_population, max_population=run.max_population, min_search_volume=run.min_search_volume, da_threshold=run.da_threshold, required_low_da_count=run.required_low_da_count, organic_depth=run.organic_depth)


def create_recalculation(db, project_id: str, profile: ValidationProfile, parent_run_id: str | None = None, candidate_ids: list[str] | None = None, freshness_policy: FreshnessPolicy = FreshnessPolicy.REUSE_FRESH_ONLY) -> Run:
    minimum_weak = profile.required_low_da_count
    run = Run(project_id=project_id, run_type="RECALCULATION", parent_run_id=parent_run_id, freshness_policy=freshness_policy, min_population=profile.min_population, max_population=profile.max_population, min_search_volume=profile.min_search_volume, da_threshold=profile.da_threshold, required_low_da_count=minimum_weak, minimum_weak_domains=minimum_weak, ideal_weak_domains=profile.ideal_weak_domains, authority_evaluation_mode=profile.authority_evaluation_mode, authority_batch_size=profile.authority_batch_size, adaptive_seek_ideal=profile.adaptive_seek_ideal, organic_depth=profile.organic_depth, kd_enabled=profile.kd_enabled, kd_provider=profile.kd_provider, kd_threshold=profile.kd_threshold, kd_operator=profile.kd_operator, kd_mode=profile.kd_mode, country_code="US", language_code="en", configuration_snapshot=profile.model_dump(), enabled_gates={"population": True, "search_volume": True, "authority": True})
    db.add(run); db.commit(); db.refresh(run)
    return run


def preview_recalculation(db, project_id: str, profile: ValidationProfile, candidate_ids: list[str] | None = None) -> dict:
    stmt = select(ProjectCandidate).where(ProjectCandidate.project_id == project_id)
    if candidate_ids:
        stmt = stmt.where(ProjectCandidate.id.in_(candidate_ids))
    candidates = db.scalars(stmt).all()
    affected = len(candidates)
    sv_reusable = 0; kd_reusable = 0; population_reusable = 0; serp_reusable = 0; authority_reusable = 0; da_changeable = 0
    for candidate in candidates:
        latest = db.scalar(select(SearchVolumeEvidence).join(RunCandidate, RunCandidate.search_volume_evidence_id == SearchVolumeEvidence.id).where(RunCandidate.project_candidate_id == candidate.id).order_by(SearchVolumeEvidence.fetched_at.desc()))
        if latest and latest.avg_monthly_searches is not None:
            sv_reusable += 1
        if latest:
            kd_reusable += int(db.scalar(select(KeywordDifficultyEvidence).where(KeywordDifficultyEvidence.candidate_entity_id == candidate.candidate_entity_id).order_by(KeywordDifficultyEvidence.fetched_at.desc())) is not None)
        prior = db.scalar(select(RunCandidate).where(RunCandidate.project_candidate_id == candidate.id).order_by(RunCandidate.created_at.desc()))
        if prior and prior.population_evidence_id:
            population_reusable += 1
        if prior and prior.serp_snapshot_id:
            snap = db.get(SerpSnapshot, prior.serp_snapshot_id)
            if snap and snap.requested_depth >= profile.organic_depth:
                serp_reusable += 1
                if db.query(RunCandidateAuthorityEvidence).filter_by(run_candidate_id=prior.id).count() >= profile.organic_depth:
                    authority_reusable += 1
                    da_changeable += 1
    fresh_sv = affected - sv_reusable
    fresh_serp = affected - serp_reusable
    fresh_authority = affected - authority_reusable
    fresh_kd = affected - kd_reusable
    from app.providers.runtime_config import DataForSEOConfig
    dfs = DataForSEOConfig()
    max_authority = affected * profile.organic_depth
    return {"total_affected": affected, "population_reusable": population_reusable, "sv_evidence_reusable": sv_reusable, "kd_evidence_reusable": kd_reusable, "serp_evidence_reusable": serp_reusable, "authority_evidence_reusable": authority_reusable, "da_outcomes_recomputable": da_changeable, "candidates_requiring_fresh_sv": fresh_sv, "candidates_requiring_fresh_kd": fresh_kd, "candidates_requiring_fresh_serp": fresh_serp, "candidates_requiring_fresh_authority": fresh_authority, "reusable_evidence_by_stage": {"population": population_reusable, "search_volume": sv_reusable, "keyword_difficulty": kd_reusable, "serp": serp_reusable, "authority": authority_reusable}, "estimated_provider_calls_by_stage": {"sv": fresh_sv, "keyword_difficulty": fresh_kd, "serp": fresh_serp, "authority": fresh_authority}, "estimated_provider_calls": fresh_sv + fresh_kd + fresh_serp + fresh_authority, "estimated_cost": fresh_serp * dfs.standard_serp_cost, "cost_confidence": "KNOWN", "dataforseo_mode": dfs.mode.value, "dataforseo_serps_required": fresh_serp, "organic_depth": profile.organic_depth, "maximum_authority_targets": {"value": max_authority, "confidence": "UPPER_BOUND"}, "compatible_cached_authority_targets": authority_reusable * profile.organic_depth, "fresh_authority_upper_bound": max(0, max_authority - authority_reusable * profile.organic_depth), "authority_mode": profile.authority_evaluation_mode, "minimum_weak_domains": profile.required_low_da_count, "ideal_weak_domains": profile.ideal_weak_domains, "seek_ideal": profile.adaptive_seek_ideal, "adaptive_batch_size": profile.authority_batch_size, "adaptive_target_estimate": {"value": max(0, max_authority - authority_reusable * profile.organic_depth), "confidence": "ESTIMATE" if profile.authority_evaluation_mode == "ADAPTIVE" else "UPPER_BOUND"}}


async def recalculate(db, project_id: str, profile: ValidationProfile, parent_run_id: str | None = None, candidate_ids: list[str] | None = None) -> Run:
    run = create_recalculation(db, project_id, profile, parent_run_id, candidate_ids)
    stmt = select(ProjectCandidate).where(ProjectCandidate.project_id == project_id)
    if candidate_ids:
        stmt = stmt.where(ProjectCandidate.id.in_(candidate_ids))
    candidates = db.scalars(stmt).all()
    fast_count = 0
    for pc in candidates:
        prior = db.scalar(select(RunCandidate).where(RunCandidate.project_candidate_id == pc.id, RunCandidate.finished_at.is_not(None)).order_by(RunCandidate.created_at.desc()))
        if not prior or not prior.population_evidence_id or not prior.search_volume_evidence_id or not prior.serp_snapshot_id:
            continue
        snap = db.get(SerpSnapshot, prior.serp_snapshot_id)
        lineage = db.scalars(select(RunCandidateAuthorityEvidence).where(RunCandidateAuthorityEvidence.run_candidate_id == prior.id).order_by(RunCandidateAuthorityEvidence.ranking_position)).all()
        if not snap or snap.requested_depth < profile.organic_depth or len(lineage) < profile.organic_depth:
            continue
        sv = db.get(SearchVolumeEvidence, prior.search_volume_evidence_id)
        pop = db.get(PopulationEvidence, prior.population_evidence_id)
        kd = db.get(KeywordDifficultyEvidence, prior.keyword_difficulty_evidence_id) if prior.keyword_difficulty_evidence_id else None
        if not sv or not pop or sv.avg_monthly_searches is None:
            continue
        rc = RunCandidate(run_id=run.id, project_candidate_id=pc.id, population_evidence_id=pop.id, search_volume_evidence_id=sv.id, keyword_difficulty_evidence_id=kd.id if kd else None, serp_snapshot_id=snap.id, da_threshold_used=profile.da_threshold, required_low_da_count_used=profile.required_low_da_count, minimum_weak_domains_used=profile.required_low_da_count, ideal_weak_domains_used=profile.ideal_weak_domains, authority_evaluation_mode_used=profile.authority_evaluation_mode, adaptive_seek_ideal_used=profile.adaptive_seek_ideal, organic_results_evaluated=profile.organic_depth, kd_value_used=kd.difficulty if kd else None, kd_status=("IDEAL" if kd and kd.difficulty is not None and kd.difficulty < profile.kd_threshold else "ABOVE_PREFERRED") if kd else "MISSING")
        db.add(rc); db.flush()
        if pop.population < profile.min_population or pop.population > profile.max_population:
            rc.status="POPULATION_REJECTED"; rc.reason_codes=["POPULATION_BELOW_MIN" if pop.population < profile.min_population else "POPULATION_ABOVE_MAX"]
        elif sv.avg_monthly_searches < profile.min_search_volume:
            rc.status="SV_REJECTED"; rc.reason_codes=["SV_BELOW_THRESHOLD"]
        elif profile.kd_enabled and profile.kd_mode == "HARD_GATE" and kd and kd.difficulty is not None and kd.difficulty >= profile.kd_threshold:
            rc.status="PRIMARY_REJECTED"; rc.automatic_status="PRIMARY_REJECTED"; rc.primary_gate_passed=False; rc.reason_codes=["KD_ABOVE_THRESHOLD"]
        else:
            selected = lineage[:profile.organic_depth]; available = sum(1 for x in selected if x.da_value_used is not None); low = sum(1 for x in selected if x.da_value_used is not None and x.da_value_used < profile.da_threshold)
            rc.authority_results_available=available; rc.low_da_count=low; rc.authority_targets_evaluated=available; rc.authority_targets_cached=len(selected); rc.authority_targets_fetched=0; rc.authority_targets_unchecked=max(0, profile.organic_depth - available); rc.confirmed_weak_count=low; rc.opportunity_classification="IDEAL" if low >= profile.ideal_weak_domains else ("PASS" if low >= profile.required_low_da_count else "FAIL")
            if available < profile.organic_depth:
                rc.status="ERROR_RETRYABLE"; rc.reason_codes=["DATA_INCOMPLETE"]
            elif low < profile.required_low_da_count:
                rc.status="PRIMARY_REJECTED"; rc.automatic_status="PRIMARY_REJECTED"; rc.primary_gate_passed=False; rc.reason_codes=["LOW_DA_COUNT_BELOW_REQUIRED"]
            else:
                rc.status="PASS"; rc.automatic_status="PASS"; rc.primary_gate_passed=True
            for old in selected:
                db.add(RunCandidateAuthorityEvidence(run_candidate_id=rc.id, serp_result_row_id=old.serp_result_row_id, authority_evidence_id=old.authority_evidence_id, ranking_position=old.ranking_position, da_value_used=old.da_value_used, counted_as_low_da=old.da_value_used is not None and old.da_value_used < profile.da_threshold))
        rc.finished_at = utc_now(); db.flush()
        db.add(CandidateEvent(run_id=run.id, run_candidate_id=rc.id, project_candidate_id=pc.id, event_type="RECALCULATION_COMPLETED", resulting_status=rc.status, evidence_references={"population": pop.id, "search_volume": sv.id, "serp": snap.id}, metadata_json={"parent_run_id": parent_run_id}))
        if rc.status in ("PASS", "PRIMARY_REJECTED", "SV_REJECTED", "POPULATION_REJECTED"):
            pc.current_status=rc.status; pc.automatic_status=rc.automatic_status; pc.current_reason_codes=rc.reason_codes; pc.latest_run_id=run.id
        fast_count += 1
    if fast_count == len(candidates) and candidates:
        run.status="COMPLETED"; run.counters={"total_selected": len(candidates), "evidence_reused": fast_count, "provider_calls": 0}; run.finished_at=utc_now(); db.commit(); db.refresh(run); return run
    db.commit()
    return await execute_run(db, run.id, candidate_ids)


def ledger(db, project_id: str, page: int = 1, page_size: int = 50, status: str | None = None,
           broad_category: str | None = None, micro_niche: str | None = None,
           nano_niche: str | None = None, state: str | None = None,
           min_population: int | None = None, max_population: int | None = None,
           min_sv: int | None = None, max_sv: int | None = None,
           min_kd: float | None = None, max_kd: float | None = None,
           kd_provider: str | None = None, kd_status: str | None = None,
           min_low_da: int | None = None, primary_result: str | None = None,
           reason_code: str | None = None):
    stmt = select(ProjectCandidate).join(CandidateEntity, CandidateEntity.id == ProjectCandidate.candidate_entity_id).join(City, City.id == CandidateEntity.city_id).where(ProjectCandidate.project_id == project_id)
    if status:
        stmt = stmt.where(ProjectCandidate.current_status == status)
    if broad_category: stmt = stmt.where(ProjectCandidate.broad_category == broad_category)
    if micro_niche: stmt = stmt.where(ProjectCandidate.micro_niche == micro_niche)
    if nano_niche: stmt = stmt.where(ProjectCandidate.nano_niche == nano_niche)
    if state: stmt = stmt.where(City.state_code == state.upper())
    if min_population is not None: stmt = stmt.where(City.population >= min_population)
    if max_population is not None: stmt = stmt.where(City.population <= max_population)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(ProjectCandidate.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    items=[]
    for row in rows:
        latest = db.scalar(select(RunCandidate).where(RunCandidate.project_candidate_id == row.id).order_by(RunCandidate.created_at.desc()))
        sv = db.get(SearchVolumeEvidence, latest.search_volume_evidence_id) if latest and latest.search_volume_evidence_id else None
        kd = db.get(KeywordDifficultyEvidence, latest.keyword_difficulty_evidence_id) if latest and latest.keyword_difficulty_evidence_id else None
        if min_sv is not None and (sv is None or sv.avg_monthly_searches is None or sv.avg_monthly_searches < min_sv): continue
        if max_sv is not None and (sv is None or sv.avg_monthly_searches is None or sv.avg_monthly_searches > max_sv): continue
        if min_kd is not None and (kd is None or kd.difficulty is None or kd.difficulty < min_kd): continue
        if max_kd is not None and (kd is None or kd.difficulty is None or kd.difficulty > max_kd): continue
        if kd_provider and (kd is None or kd.provider != kd_provider): continue
        if kd_status and (latest is None or latest.kd_status != kd_status): continue
        if min_low_da is not None and (latest is None or latest.low_da_count is None or latest.low_da_count < min_low_da): continue
        if primary_result and (latest is None or latest.status != primary_result): continue
        if reason_code and (not row.current_reason_codes or reason_code not in row.current_reason_codes): continue
        items.append({"project_candidate_id": row.id, "display_keyword": row.display_keyword, "broad_category": row.broad_category, "micro_niche": row.micro_niche, "nano_niche": row.nano_niche, "current_status": row.current_status, "automatic_status": row.automatic_status, "manual_status": row.manual_status, "reason_codes": row.current_reason_codes, "latest_run_id": row.latest_run_id, "latest_search_volume": sv.avg_monthly_searches if sv else None, "search_volume_provider": sv.provider if sv else None, "search_volume_fetched_at": sv.fetched_at.isoformat() if sv else None, "latest_kd": kd.difficulty if kd else None, "kd_provider": kd.provider if kd else None, "kd_status": latest.kd_status if latest else None, "kd_threshold": db.get(Run, latest.run_id).kd_threshold if latest else None, "historical_run_count": db.query(RunCandidate).filter_by(project_candidate_id=row.id).count(), "latest_low_da_count": latest.low_da_count if latest else None, "latest_da_threshold": latest.da_threshold_used if latest else None, "latest_required_low_da_count": latest.required_low_da_count_used if latest else None})
    return {"items": items, "page": page, "page_size": page_size, "total": total}


def candidate_history(db, project_candidate_id: str):
    run_candidates = db.scalars(select(RunCandidate).where(RunCandidate.project_candidate_id == project_candidate_id).order_by(RunCandidate.created_at)).all()
    details=[]
    for rc in run_candidates:
        run=db.get(Run, rc.run_id); lineage=db.scalars(select(RunCandidateAuthorityEvidence).where(RunCandidateAuthorityEvidence.run_candidate_id == rc.id).order_by(RunCandidateAuthorityEvidence.ranking_position)).all()
        authority=[]
        for link in lineage:
            ev=db.get(AuthorityEvidence, link.authority_evidence_id); result=db.get(SerpResultRow, link.serp_result_row_id)
            authority.append({"position": link.ranking_position, "url": result.url if result else None, "root_domain": result.root_domain if result else None, "da_used": link.da_value_used, "weak": link.counted_as_low_da, "provider": ev.provider if ev else None, "source_kind": ev.source_kind if ev else None, "fetched_at": ev.fetched_at.isoformat() if ev else None})
        kd = db.get(KeywordDifficultyEvidence, rc.keyword_difficulty_evidence_id) if rc.keyword_difficulty_evidence_id else None
        details.append({"run_id": rc.run_id, "run_type": run.run_type if run else None, "parent_run_id": run.parent_run_id if run else None, "status": rc.status, "automatic_status": rc.automatic_status, "reason_codes": rc.reason_codes, "thresholds": {"da": rc.da_threshold_used, "required_low_da": rc.required_low_da_count_used, "kd": run.kd_threshold if run else None, "kd_mode": run.kd_mode if run else None}, "population_evidence_id": rc.population_evidence_id, "search_volume_evidence_id": rc.search_volume_evidence_id, "keyword_difficulty_evidence_id": rc.keyword_difficulty_evidence_id, "kd_value_used": rc.kd_value_used, "kd_status": rc.kd_status, "serp_snapshot_id": rc.serp_snapshot_id, "low_da_count": rc.low_da_count, "authority_lineage": authority})
    return {"project_candidate_id": project_candidate_id, "runs": details, "events": db.scalars(select(CandidateEvent).where(CandidateEvent.project_candidate_id == project_candidate_id).order_by(CandidateEvent.created_at)).all()}
