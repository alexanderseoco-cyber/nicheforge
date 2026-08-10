from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.entities import CandidateEntity, City, ImportBatch, KeywordDifficultyEvidence, Project, ProjectCandidate, SearchVolumeEvidence
from app.services.imports import export_candidate_history_csv, export_project_csv, export_run_csv, import_cities, import_keyword_export, import_manual_evidence, import_moz, import_niches
from app.services.recalculation import candidate_history


def test_niche_csv_and_keywords_everywhere_import_are_provenanced_and_hash_deduplicated():
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine)
    with Session(engine) as db:
        project = Project(name="Imports", profile_snapshot={}); city = City(name="Salina", state_code="KS", population=47000, population_vintage="test"); db.add_all([project, city]); db.commit()
        niche = b"broad_category,micro_niche,service_term\nPest,Residential,rodent control\n"
        first = import_niches(db, project.id, niche, "niches.csv")
        second = import_niches(db, project.id, niche, "niches.csv")
        assert first["accepted"] == 1 and second["duplicate_file"] is True
        csv_data = b"Keyword,Volume,CPC,Competition,KD,Location\nrodent control salina ks,320,4.5,0.2,12,Salina KS\n"
        result = import_keyword_export(db, project.id, csv_data, "keywords_everywhere_csv", "ke.csv")
        assert result["accepted"] == 1
        sv = db.scalar(select(SearchVolumeEvidence).where(SearchVolumeEvidence.provider == "keywords_everywhere_csv"))
        kd = db.scalar(select(KeywordDifficultyEvidence).where(KeywordDifficultyEvidence.provider == "keywords_everywhere_csv"))
        assert sv.avg_monthly_searches == 320 and sv.source_kind == "keywords_everywhere_csv"
        assert kd.difficulty == 12 and kd.provider != "moz"
        assert db.query(ImportBatch).count() == 2


def test_unresolved_localized_import_is_retained_in_report():
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine)
    with Session(engine) as db:
        project = Project(name="Imports", profile_snapshot={}); db.add(project); db.commit()
        result = import_keyword_export(db, project.id, b"keyword,volume\ntermite control nowhere zz,100\n", "ahrefs_csv", "ahrefs.csv")
        batch = db.get(ImportBatch, result["import_batch_id"])
        assert result["unresolved"] == 1 and batch.error_summary["unresolved_count"] == 1


def test_city_import_preserves_vintages_and_conflicts():
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine)
    with Session(engine) as db:
        project = Project(name="Cities", profile_snapshot={}); db.add(project); db.commit()
        first = import_cities(db, b"city,state,population,vintage,census_geo_id\nSalina,KS,47000,2020,US1\n", "cities.csv", project.id)
        newer = import_cities(db, b"city,state,population,vintage,census_geo_id\nSalina,KS,48000,2023,US1\n", "cities-new.csv", project.id)
        conflict = import_cities(db, b"city,state,population,vintage,census_geo_id\nSalina,KS,49000,2023,US2\n", "cities-conflict.csv", project.id)
        assert first["accepted"] == 1 and newer["accepted"] == 1 and conflict["conflicts"] == 1
        assert db.query(City).count() == 2


def test_run_export_uses_pinned_evidence_not_newer_observation():
    from tests.test_pipeline import seeded_db
    from app.services.run_pipeline import execute_run
    db, run, candidate = seeded_db(); import asyncio; asyncio.run(execute_run(db, run.id, [candidate.id]))
    old_rc = db.query(__import__('app.models.entities', fromlist=['RunCandidate']).RunCandidate).filter_by(run_id=run.id).one()
    old_sv = db.get(SearchVolumeEvidence, old_rc.search_volume_evidence_id).avg_monthly_searches
    db.add(SearchVolumeEvidence(candidate_entity_id=old_rc.project_candidate_id, keyword="rodent control salina ks", location_name="Salina, KS", provider="keywords_everywhere_csv", source_kind="keywords_everywhere_csv", avg_monthly_searches=9999)); db.commit()
    exported = export_run_csv(db, run.id)
    assert str(old_sv) in exported and "9999" not in exported


def test_moz_and_manual_imports_preserve_metric_scope_and_source():
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine)
    with Session(engine) as db:
        project = Project(name="Moz", profile_snapshot={}); city = City(name="Salina", state_code="KS", population=47000, population_vintage="test"); db.add_all([project, city]); db.commit()
        result = import_moz(db, project.id, b"Keyword,URL,Domain,KD,DA,PA,Spam Score\nrodent control salina ks,https://example.com/a,example.com,12,8,4,2\n", "moz.csv")
        assert result["accepted"] == 1
        rows = db.query(KeywordDifficultyEvidence).all(); authority = db.query(__import__('app.models.entities', fromlist=['AuthorityEvidence']).AuthorityEvidence).all()
        assert rows[0].provider == "moz_csv" and authority[0].provider == "moz_csv" and authority[0].target_type == "URL"
        manual = import_manual_evidence(db, project.id, {"keyword": "rodent control salina ks", "metric_type": "keyword_difficulty", "value": 9, "note": "checked"})
        assert manual["accepted"] == 1 and db.query(KeywordDifficultyEvidence).filter_by(source_kind="manual").count() == 1


def test_ahrefs_serp_expanded_rows_are_detected_and_logically_deduplicated():
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine)
    with Session(engine) as db:
        project = Project(name="Ahrefs", profile_snapshot={}); city = City(name="Salina", state_code="KS", population=47000, population_vintage="test"); db.add_all([project, city]); db.commit()
        content = b"Keyword,Volume,KD,URL\nrodent control salina ks,300,18,https://a.example\nrodent control salina ks,300,18,https://b.example\n"
        result = import_keyword_export(db, project.id, content, "ahrefs_csv", "serp.csv")
        assert result["format"] == "serp_expanded" and result["deduplicated"] == 1
        assert db.query(ProjectCandidate).count() == 1
        batch = db.get(ImportBatch, result["import_batch_id"])
        assert batch.error_summary["deduplicated_count"] == 1


def test_imported_ke_sv_and_moz_kd_are_consumed_by_normal_run_pipeline(monkeypatch):
    import pytest
    import asyncio
    from app.models.entities import Run, ProviderCall
    from app.services.run_pipeline import execute_run
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine)
    with Session(engine) as db:
        project = Project(name="Integrated imports", profile_snapshot={}); city = City(name="Salina", state_code="KS", population=47000, population_vintage="test"); db.add_all([project, city]); db.commit()
        csv_data = b'Keyword,Volume,CPC,Competition,Location\nrodent control salina ks,500,4,0.2,"Salina, KS"\n'
        import_keyword_export(db, project.id, csv_data, "keywords_everywhere_csv", "ke-integrated.csv")
        import_moz(db, project.id, b"Keyword,KD\nrodent control salina ks,12\n", "moz-kd.csv")
        pc = db.query(ProjectCandidate).one(); run = Run(project_id=project.id, min_population=20000, max_population=120000, min_search_volume=300, da_threshold=10, required_low_da_count=0, organic_depth=10, kd_threshold=15, kd_mode="PRIORITY"); db.add(run); db.commit()
        asyncio.run(execute_run(db, run.id, [pc.id]))
        rc = db.query(__import__('app.models.entities', fromlist=['RunCandidate']).RunCandidate).filter_by(run_id=run.id).one()
        assert rc.search_volume_evidence_id and rc.keyword_difficulty_evidence_id and rc.kd_status == "IDEAL"
        assert db.query(ProviderCall).filter(ProviderCall.stage == "sv", ProviderCall.outcome == "success").count() == 0


def test_imported_moz_authority_drives_da_gate_without_authority_provider_call(monkeypatch):
    import asyncio
    from app.services.run_pipeline import execute_run
    from app.models.entities import Run, ProviderCall
    from app.providers.contracts import OrganicResult, SerpResult
    import app.services.run_pipeline as pipeline
    class OneResult:
        async def fetch(self, requests):
            return [SerpResult(r.keyword, [OrganicResult(1, "Imported", "https://imported.example/service")], "mock") for r in requests]
    class MustNotCall:
        async def fetch(self, targets): raise AssertionError("authority provider should not be called")
    monkeypatch.setattr(pipeline, "serp_provider", lambda: OneResult())
    monkeypatch.setattr(pipeline, "authority_provider", lambda: MustNotCall())
    monkeypatch.setattr(pipeline, "root_domain", lambda url: "imported.example")
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine)
    with Session(engine) as db:
        project = Project(name="Moz authority", profile_snapshot={}); city = City(name="Salina", state_code="KS", population=47000, population_vintage="test"); db.add_all([project, city]); db.commit()
        import_keyword_export(db, project.id, b'Keyword,Volume,Location\nrodent control salina ks,500,"Salina, KS"\n', "keywords_everywhere_csv", "ke.csv")
        import_moz(db, project.id, b"Keyword,URL,Domain,DA,PA\nrodent control salina ks,https://imported.example/service,imported.example,5,4\n", "moz.csv")
        pc = db.query(ProjectCandidate).one(); run = Run(project_id=project.id, min_population=20000, max_population=120000, min_search_volume=300, da_threshold=10, required_low_da_count=1, organic_depth=1, kd_enabled=False); db.add(run); db.commit()
        asyncio.run(execute_run(db, run.id, [pc.id]))
        rc = db.query(__import__('app.models.entities', fromlist=['RunCandidate']).RunCandidate).filter_by(run_id=run.id).one()
        errors = db.query(__import__('app.models.entities', fromlist=['CandidateEvent']).CandidateEvent).all()
        assert rc.status == "PASS", [e.metadata_json for e in errors][-1]
        assert db.query(ProviderCall).filter(ProviderCall.stage == "authority", ProviderCall.outcome == "success").count() == 0


def test_ahrefs_kd_is_not_consumed_by_moz_configured_run():
    import asyncio
    from app.models.entities import Run
    from app.services.run_pipeline import execute_run
    engine = create_engine("sqlite:///:memory:"); Base.metadata.create_all(engine)
    with Session(engine) as db:
        project = Project(name="Provider separation", profile_snapshot={}); city = City(name="Salina", state_code="KS", population=47000, population_vintage="test"); db.add_all([project, city]); db.commit()
        import_keyword_export(db, project.id, b'Keyword,Volume,KD,Location\nrodent control salina ks,500,8,"Salina, KS"\n', "ahrefs_csv", "ahrefs.csv")
        pc = db.query(ProjectCandidate).one(); run = Run(project_id=project.id, min_population=20000, max_population=120000, min_search_volume=300, da_threshold=10, required_low_da_count=0, organic_depth=10, kd_provider="moz", kd_threshold=15); db.add(run); db.commit()
        asyncio.run(execute_run(db, run.id, [pc.id]))
        rc = db.query(__import__('app.models.entities', fromlist=['RunCandidate']).RunCandidate).filter_by(run_id=run.id).one()
        assert rc.keyword_difficulty_evidence_id is None
        assert db.query(KeywordDifficultyEvidence).filter_by(provider="ahrefs_csv").count() == 1


def test_file_backed_import_run_recalculation_export_restart_acceptance(tmp_path):
    import asyncio
    from app.models.entities import Run
    from app.services.run_pipeline import execute_run
    from app.services.recalculation import recalculate
    path = tmp_path / "imports.sqlite3"; engine = create_engine(f"sqlite:///{path}"); Base.metadata.create_all(engine)
    with Session(engine) as db:
        project = Project(name="F acceptance", profile_snapshot={}); city = City(name="Salina", state_code="KS", population=47000, population_vintage="2020", census_geo_id="US1"); db.add_all([project, city]); db.commit()
        import_cities(db, b"city,state,population,vintage,census_geo_id\nSalina,KS,47000,2020,US1\n", "city.csv", project.id)
        import_keyword_export(db, project.id, b'Keyword,Volume,Location\nrodent control salina ks,500,"Salina, KS"\n', "keywords_everywhere_csv", "ke.csv")
        import_keyword_export(db, project.id, b'Keyword,Volume,KD,Location\nrodent control salina ks,450,8,"Salina, KS"\n', "ahrefs_csv", "ahrefs.csv")
        import_moz(db, project.id, b"Keyword,KD\nrodent control salina ks,12\n", "moz.csv")
        pc = db.query(ProjectCandidate).one(); run_a = Run(project_id=project.id, min_population=20000, max_population=120000, min_search_volume=300, da_threshold=10, required_low_da_count=0, organic_depth=10, kd_threshold=15); db.add(run_a); db.commit(); asyncio.run(execute_run(db, run_a.id, [pc.id]))
        run_b = asyncio.run(recalculate(db, project.id, __import__('app.schemas.domain', fromlist=['ValidationProfile']).ValidationProfile(min_population=20000, max_population=120000, min_search_volume=250, da_threshold=10, required_low_da_count=0, organic_depth=10, kd_threshold=20), parent_run_id=run_a.id, candidate_ids=[pc.id]))
        old_export = export_run_csv(db, run_a.id); history_export = export_candidate_history_csv(db, pc.id); project_export = export_project_csv(db, project.id); ids = (project.id, pc.id, run_a.id, run_b.id)
    engine.dispose()
    reopened = create_engine(f"sqlite:///{path}")
    with Session(reopened) as db:
        project_id, pc_id, run_a_id, run_b_id = ids
        assert db.query(ImportBatch).count() >= 4 and db.query(KeywordDifficultyEvidence).filter_by(provider="moz_csv").count() == 1
        assert db.get(Run, run_b_id).parent_run_id == run_a_id
        assert str(run_a_id) in old_export and str(run_a_id) in history_export and str(pc_id) in project_export
        assert len(candidate_history(db, pc_id)["runs"]) == 2
    reopened.dispose()
