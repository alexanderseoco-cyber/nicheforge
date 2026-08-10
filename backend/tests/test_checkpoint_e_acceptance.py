import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.entities import CandidateEntity, City, Project, ProjectCandidate, ProviderCall, RunCandidate
from app.providers.contracts import AuthorityResult, KeywordMetricResult, OrganicResult, SerpResult
from app.schemas.domain import ValidationProfile
from app.services.identity import canonical_identity, identity_key
from app.services.recalculation import candidate_history, ledger, recalculate
from app.services.run_pipeline import execute_run


class AcceptanceSV:
    values = {"A": 500, "B": 100, "C": 500, "D": 500, "E": 500, "F": 500, "G": 500}
    kd = {"A": 5, "B": 5, "C": 5, "D": 10, "E": 17, "F": 17, "G": 10}
    async def fetch(self, requests):
        return [KeywordMetricResult(r.keyword, self.values[r.keyword[0]], keyword_difficulty=self.kd[r.keyword[0]], provider="mock") for r in requests]


class AcceptanceSERP:
    async def fetch(self, requests):
        out = []
        for r in requests:
            key = r.keyword[0]
            organic = [] if key == "G" else [OrganicResult(i, f"{key} result {i}", f"https://{key.lower()}-{i}.example/service") for i in range(1, 11)]
            out.append(SerpResult(r.keyword, organic, "mock"))
        return out


class AcceptanceAuthority:
    async def fetch(self, targets):
        return [AuthorityResult(t.url, t.root_domain, da=20 if t.url.startswith("https://c-") else 5, provider="mock") for t in targets]


@pytest.mark.asyncio
async def test_final_checkpoint_e_multi_candidate_acceptance(monkeypatch):
    import app.services.run_pipeline as pipeline
    monkeypatch.setattr(pipeline, "search_volume_provider", lambda: AcceptanceSV())
    monkeypatch.setattr(pipeline, "serp_provider", lambda: AcceptanceSERP())
    monkeypatch.setattr(pipeline, "authority_provider", lambda: AcceptanceAuthority())

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        city = City(name="Acceptance", state_code="KS", population=47000, population_vintage="test")
        low_city = City(name="Small", state_code="KS", population=1000, population_vintage="test")
        project = Project(name="Acceptance", profile_snapshot={}); db.add_all([city, low_city, project]); db.flush()
        pcs = []
        for key in "ABCDEFG":
            c = canonical_identity(f"service {key}", f"US-{key}")
            entity = CandidateEntity(canonical_identity=c, identity_key=identity_key(c), service_term_normalized=f"service {key}", city_id=low_city.id if key == "A" else city.id, canonical_keyword=key)
            db.add(entity); db.flush(); pc = ProjectCandidate(project_id=project.id, candidate_entity_id=entity.id, display_keyword=key); db.add(pc); db.flush(); pcs.append(pc)
        from app.models.entities import Run
        run_a = Run(project_id=project.id, min_population=20000, max_population=120000, min_search_volume=300, da_threshold=10, required_low_da_count=5, organic_depth=10, kd_threshold=15, kd_mode="PRIORITY")
        db.add(run_a); db.commit()
        await execute_run(db, run_a.id, [p.id for p in pcs])
        results_a = {p.display_keyword: db.scalar(select(RunCandidate).where(RunCandidate.run_id == run_a.id, RunCandidate.project_candidate_id == p.id)) for p in pcs}
        assert results_a["A"].status == "POPULATION_REJECTED"
        assert results_a["B"].status == "SV_REJECTED"
        assert results_a["C"].status == "PRIMARY_REJECTED"
        assert results_a["D"].status == "PASS" and results_a["D"].kd_status == "IDEAL"
        assert results_a["E"].status == "PASS" and results_a["E"].kd_status == "ABOVE_PREFERRED"
        assert results_a["F"].status == "PASS" and results_a["F"].kd_status == "ABOVE_PREFERRED"
        assert results_a["G"].status == "ERROR_RETRYABLE"
        assert results_a["A"].search_volume_evidence_id is None and results_a["B"].serp_snapshot_id is None
        calls_a = db.query(ProviderCall).count()
        hard_gate = ValidationProfile(min_population=20000, max_population=120000, min_search_volume=300, da_threshold=10, required_low_da_count=5, organic_depth=10, kd_threshold=15, kd_mode="HARD_GATE")
        run_f = await recalculate(db, project.id, hard_gate, parent_run_id=run_a.id, candidate_ids=[pcs[5].id])
        f_gate = db.scalar(select(RunCandidate).where(RunCandidate.run_id == run_f.id))
        assert f_gate.status == "PRIMARY_REJECTED" and "KD_ABOVE_THRESHOLD" in f_gate.reason_codes
        profile = ValidationProfile(min_population=20000, max_population=120000, min_search_volume=250, da_threshold=10, required_low_da_count=4, organic_depth=10, kd_threshold=20, kd_mode="HARD_GATE")
        run_b = await recalculate(db, project.id, profile, parent_run_id=run_a.id, candidate_ids=[p.id for p in pcs])
        results_b = {p.display_keyword: db.scalar(select(RunCandidate).where(RunCandidate.run_id == run_b.id, RunCandidate.project_candidate_id == p.id)) for p in pcs}
        assert results_b["D"].status == "PASS" and results_b["D"].keyword_difficulty_evidence_id == results_a["D"].keyword_difficulty_evidence_id
        assert results_b["E"].kd_status == "IDEAL" and results_b["E"].status == "PASS"
        assert results_b["C"].status == "PRIMARY_REJECTED"
        assert results_a["E"].status == "PASS" and results_a["E"].kd_status == "ABOVE_PREFERRED"
        assert db.query(ProviderCall).filter(ProviderCall.outcome == "success").count() == db.query(ProviderCall).filter(ProviderCall.outcome == "success", ProviderCall.run_id == run_a.id).count()
        assert db.query(ProviderCall).filter(ProviderCall.cache_hit == True).count() > 0
        assert run_b.parent_run_id == run_a.id
        assert ledger(db, project.id)["total"] == 7
        assert len(candidate_history(db, pcs[4].id)["runs"]) >= 2
