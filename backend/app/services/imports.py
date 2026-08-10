from __future__ import annotations

import csv
import hashlib
import io
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import AuthorityEvidence, CandidateEntity, City, ImportBatch, KeywordDifficultyEvidence, PopulationEvidence, ProjectCandidate, ProviderCache, Run, RunCandidate, SearchVolumeEvidence
from app.services.identity import canonical_identity, identity_key
from app.services.normalization import normalize_keyword
from app.services.cache_keys import provider_cache_key

MAX_IMPORT_BYTES = 25 * 1024 * 1024
MAX_IMPORT_ROWS = 250000
MAX_FIELD_LENGTH = 2000


def _utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _batch(db, project_id, source_kind, filename, raw):
    if len(raw) > MAX_IMPORT_BYTES:
        raise ValueError("Import exceeds the operational upload-size limit")
    digest = hashlib.sha256(raw).hexdigest()
    duplicate = db.scalar(select(ImportBatch).where(ImportBatch.project_id == project_id, ImportBatch.file_hash == digest, ImportBatch.source_kind == source_kind))
    if duplicate:
        return duplicate, True
    batch = ImportBatch(project_id=project_id, source_kind=source_kind, provider=source_kind, file_name=filename, file_hash=digest, created_at=_utc_now())
    db.add(batch); db.flush()
    return batch, False


def import_niches(db: Session, project_id: str, content: bytes, filename: str = "niches.csv"):
    batch, duplicate = _batch(db, project_id, "niche_csv", filename, content)
    if duplicate:
        return {"import_batch_id": batch.id, "duplicate_file": True, "accepted": 0, "rejected": 0, "unresolved": 0}
    text = content.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text))) if "," in text.splitlines()[0] else [{"service_term": line.strip()} for line in text.splitlines() if line.strip()]
    accepted = rejected = 0
    for row in rows:
        service = (row.get("service_term") or row.get("keyword") or next(iter(row.values()), "")).strip()
        if not service:
            rejected += 1; continue
        batch.row_count += 1; accepted += 1
        # Preserve the intake row in the report; candidate generation remains a separate operation.
        batch.error_summary.setdefault("accepted_rows", []).append({"service_term": service, "raw": row})
    batch.accepted_count = accepted; batch.rejected_count = rejected; db.commit()
    return {"import_batch_id": batch.id, "duplicate_file": False, "accepted": accepted, "rejected": rejected, "unresolved": 0}


def import_cities(db: Session, content: bytes, filename: str = "cities.csv", project_id: str | None = None):
    batch, duplicate = _batch(db, project_id, "census_csv", filename, content)
    if duplicate:
        return {"import_batch_id": batch.id, "duplicate_file": True, "accepted": 0, "rejected": 0, "conflicts": 0}
    rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    if len(rows) > MAX_IMPORT_ROWS: raise ValueError("Import exceeds the operational row-count guardrail")
    accepted = rejected = conflicts = 0
    for row in rows:
        name = (row.get("city") or row.get("place") or row.get("name") or "").strip()
        state = (row.get("state") or row.get("state_code") or "").strip().upper()
        vintage = (row.get("population_vintage") or row.get("vintage") or "unknown").strip()
        try: population = int(str(row.get("population", "")).replace(",", ""))
        except ValueError: population = None
        if not name or len(state) != 2 or population is None or population < 0:
            rejected += 1; continue
        existing = db.scalar(select(City).where(City.name.ilike(name), City.state_code == state, City.population_vintage == vintage))
        if existing:
            if existing.population != population or (row.get("census_geo_id") and existing.census_geo_id != row.get("census_geo_id")):
                conflicts += 1
            continue
        city = City(name=name, state_code=state, population=population, population_vintage=vintage, census_geo_id=row.get("census_geo_id") or row.get("geo_id")); db.add(city); db.flush()
        accepted += 1
    batch.row_count = len(rows); batch.accepted_count = accepted; batch.rejected_count = rejected; report = dict(batch.error_summary or {}); report["conflict_count"] = conflicts; batch.error_summary = report; db.commit()
    return {"import_batch_id": batch.id, "duplicate_file": False, "accepted": accepted, "rejected": rejected, "conflicts": conflicts}


def _safe(value):
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


def export_run_csv(db: Session, run_id: str) -> str:
    run = db.get(Run, run_id); rows = db.scalars(select(RunCandidate).where(RunCandidate.run_id == run_id)).all()
    output = io.StringIO(); writer = csv.writer(output); writer.writerow(["run_id", "project_candidate_id", "status", "population", "search_volume", "sv_provider", "kd", "kd_provider", "kd_status", "low_da_count", "da_threshold", "required_low_da_count", "reason_codes"])
    for rc in rows:
        sv = db.get(SearchVolumeEvidence, rc.search_volume_evidence_id) if rc.search_volume_evidence_id else None; kd = db.get(KeywordDifficultyEvidence, rc.keyword_difficulty_evidence_id) if rc.keyword_difficulty_evidence_id else None; pop = db.get(PopulationEvidence, rc.population_evidence_id) if rc.population_evidence_id else None
        writer.writerow([run_id, rc.project_candidate_id, rc.status, pop.population if pop else None, sv.avg_monthly_searches if sv else None, sv.provider if sv else None, kd.difficulty if kd else None, kd.provider if kd else None, rc.kd_status, rc.low_da_count, rc.da_threshold_used, rc.required_low_da_count_used, _safe(";".join(rc.reason_codes or []))])
    return output.getvalue()


def export_project_csv(db: Session, project_id: str) -> str:
    from app.services.recalculation import ledger
    data = ledger(db, project_id, page=1, page_size=250000)
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(["project_candidate_id", "keyword", "broad_category", "micro_niche", "nano_niche", "current_status", "reason_codes", "latest_run_id", "sv", "sv_provider", "kd", "kd_provider", "kd_status", "low_da_count", "da_threshold", "required_weak_count", "manual_status"])
    for item in data["items"]:
        writer.writerow([item.get("project_candidate_id"), _safe(item.get("display_keyword")), _safe(item.get("broad_category")), _safe(item.get("micro_niche")), _safe(item.get("nano_niche")), item.get("current_status"), _safe(";".join(item.get("reason_codes") or [])), item.get("latest_run_id"), item.get("latest_search_volume"), item.get("search_volume_provider"), item.get("latest_kd"), item.get("kd_provider"), item.get("kd_status"), item.get("latest_low_da_count"), item.get("latest_da_threshold"), item.get("latest_required_low_da_count"), _safe(item.get("manual_status"))])
    return output.getvalue()


def export_candidate_history_csv(db: Session, project_candidate_id: str) -> str:
    from app.services.recalculation import candidate_history
    history = candidate_history(db, project_candidate_id); output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(["run_id", "run_type", "parent_run_id", "status", "population_evidence_id", "search_volume_evidence_id", "keyword_difficulty_evidence_id", "low_da_count", "da_threshold", "required_weak_count", "kd_value", "kd_status", "reason_codes"])
    for item in history["runs"]:
        thresholds = item.get("thresholds") or {}; writer.writerow([item.get("run_id"), item.get("run_type"), item.get("parent_run_id"), item.get("status"), item.get("population_evidence_id"), item.get("search_volume_evidence_id"), item.get("keyword_difficulty_evidence_id"), item.get("low_da_count"), thresholds.get("da"), thresholds.get("required_low_da"), item.get("kd_value_used"), item.get("kd_status"), _safe(";".join(item.get("reason_codes") or []))])
    return output.getvalue()


def _resolve_candidate(db, project_id: str, keyword: str, row: dict, batch: ImportBatch):
    normalized = normalize_keyword(keyword)
    city_name = (row.get("city") or "").strip()
    state = (row.get("state") or row.get("state_code") or "").strip().upper()
    city = None
    if city_name and state:
        city = db.scalar(select(City).where(City.name.ilike(city_name), City.state_code == state).order_by(City.population.desc()))
    if city is None:
        parts = normalized.split()
        if len(parts) >= 2 and len(parts[-1]) == 2:
            state = parts[-1].upper(); city_name = parts[-2].title()
            city = db.scalar(select(City).where(City.name.ilike(city_name), City.state_code == state).order_by(City.population.desc()))
    if city is None:
        report = dict(batch.error_summary or {}); report.setdefault("unresolved_rows", []).append(row); batch.error_summary = report; return None
    service = row.get("service_term") or " ".join(normalized.split()[:-2])
    canonical = canonical_identity(service, row.get("geo_id") or city.census_geo_id or city.id)
    entity = db.scalar(select(CandidateEntity).where(CandidateEntity.identity_key == identity_key(canonical)))
    if entity is None:
        entity = CandidateEntity(canonical_identity=canonical, identity_key=identity_key(canonical), service_term_normalized=normalize_keyword(service), city_id=city.id, canonical_keyword=normalized)
        db.add(entity); db.flush()
    membership = db.scalar(select(ProjectCandidate).where(ProjectCandidate.project_id == project_id, ProjectCandidate.candidate_entity_id == entity.id))
    if membership is None:
        membership = ProjectCandidate(project_id=project_id, candidate_entity_id=entity.id, display_keyword=keyword, original_input=row.get("original_input"), broad_category=row.get("broad_category"), micro_niche=row.get("micro_niche"), nano_niche=row.get("nano_niche"))
        db.add(membership); db.flush()
    pop_key = provider_cache_key("local", "population", city_id=city.id, vintage=city.population_vintage)
    if db.scalar(select(PopulationEvidence).where(PopulationEvidence.candidate_entity_id == entity.id, PopulationEvidence.city_id == city.id, PopulationEvidence.population_vintage == city.population_vintage)) is None:
        evidence = PopulationEvidence(candidate_entity_id=entity.id, city_id=city.id, provider="census", source_kind="census_csv", population=city.population, population_vintage=city.population_vintage, raw_payload={"city": city.name, "import_batch_id": batch.id}, source_metadata={"import_batch_id": batch.id}, fetched_at=_utc_now(), fresh_until=_utc_now().replace(year=_utc_now().year + 1))
        db.add(evidence); db.flush(); db.add(ProviderCache(cache_key=pop_key, provider="census", operation="population", evidence_type="population", evidence_id=evidence.id, fetched_at=evidence.fetched_at, fresh_until=evidence.fresh_until))
    return entity


def import_keyword_export(db: Session, project_id: str, content: bytes, source_kind: str, filename: str):
    batch, duplicate = _batch(db, project_id, source_kind, filename, content)
    if duplicate:
        return {"import_batch_id": batch.id, "duplicate_file": True, "accepted": 0, "rejected": 0, "unresolved": 0}
    try:
        stream = io.TextIOWrapper(io.BytesIO(content), encoding="utf-8-sig", newline="")
        reader = csv.DictReader(stream, strict=True)
        if not reader.fieldnames: raise ValueError("CSV header is required")
        if not any(name in reader.fieldnames for name in ("Keyword", "keyword", "Query")): raise ValueError("CSV requires a keyword header")
    except UnicodeDecodeError as exc: raise ValueError("Import must be valid UTF-8 CSV") from exc
    ahrefs_format = "keyword_level"
    accepted = unresolved = rejected = deduplicated = 0; seen_keywords = set()
    try:
      for row in reader:
        if batch.row_count >= MAX_IMPORT_ROWS: raise ValueError("Import exceeds the operational row-count guardrail")
        if any(len(str(value)) > MAX_FIELD_LENGTH for value in row.values() if value is not None): raise ValueError("CSV field exceeds the operational length limit")
        keyword = (row.get("Keyword") or row.get("keyword") or row.get("Query") or "").strip()
        if not keyword:
            rejected += 1; batch.row_count += 1; continue
        if source_kind == "ahrefs_csv" and keyword in seen_keywords:
            deduplicated += 1; ahrefs_format = "serp_expanded"; batch.row_count += 1; continue
        seen_keywords.add(keyword); batch.row_count += 1
        entity = _resolve_candidate(db, project_id, keyword, row, batch)
        if entity is None:
            unresolved += 1; continue
        def number(*names):
            for name in names:
                if row.get(name) not in (None, ""):
                    try: return float(str(row[name]).replace(",", ""))
                    except ValueError: return None
            return None
        location = row.get("Location") or ""
        sv = SearchVolumeEvidence(candidate_entity_id=entity.id, keyword=keyword, location_name=location, provider=source_kind, source_kind=source_kind, avg_monthly_searches=int(number("Volume", "Search Volume", "volume") or 0), cpc=number("CPC", "cpc"), competition=number("Competition", "competition"), monthly_history={"raw_row": row}, raw_payload=row, request_metadata={"import_batch_id": batch.id}, fetched_at=_utc_now(), fresh_until=_utc_now()+timedelta(days=30))
        db.add(sv); db.flush()
        sv_key = provider_cache_key("mock", "search_volume", keyword=keyword, location=location, language="en", country="US")
        if db.scalar(select(ProviderCache).where(ProviderCache.cache_key == sv_key)) is None:
            db.add(ProviderCache(cache_key=sv_key, provider=source_kind, operation="search_volume", evidence_type="search_volume", evidence_id=sv.id, fetched_at=sv.fetched_at, fresh_until=sv.fresh_until))
        kd_value = number("KD", "Keyword Difficulty", "Difficulty")
        if kd_value is not None:
            kd = KeywordDifficultyEvidence(candidate_entity_id=entity.id, keyword=keyword, location_name=location, provider=source_kind, source_kind=source_kind, difficulty=kd_value, raw_payload=row, request_metadata={"import_batch_id": batch.id}, fetched_at=_utc_now(), fresh_until=_utc_now()+timedelta(days=30)); db.add(kd); db.flush()
            if source_kind == "moz_csv":
                for key_provider in ("mock", "keywords_everywhere_csv", "ahrefs_csv"):
                    kd_key = provider_cache_key(key_provider, "keyword_difficulty", keyword=keyword, location=location, language="en", country="US")
                    db.add(ProviderCache(cache_key=kd_key, provider=source_kind, operation="keyword_difficulty", evidence_type="keyword_difficulty", evidence_id=kd.id, fetched_at=kd.fetched_at, fresh_until=kd.fresh_until))
        accepted += 1
    except (csv.Error, UnicodeDecodeError) as exc:
        report = dict(batch.error_summary or {}); report["parse_error"] = str(exc); batch.error_summary = report; batch.accepted_count = accepted; batch.rejected_count = rejected; db.commit(); raise ValueError(f"Malformed CSV: {exc}") from exc
    batch.accepted_count = accepted; batch.rejected_count = rejected; report = dict(batch.error_summary or {}); report["unresolved_count"] = unresolved; report["deduplicated_count"] = deduplicated; report["format"] = ahrefs_format; batch.error_summary = report; db.commit()
    return {"import_batch_id": batch.id, "duplicate_file": False, "accepted": accepted, "rejected": rejected, "unresolved": unresolved, "deduplicated": deduplicated, "format": ahrefs_format}


def import_moz(db: Session, project_id: str, content: bytes, filename: str = "moz.csv"):
    batch, duplicate = _batch(db, project_id, "moz_csv", filename, content)
    if duplicate: return {"import_batch_id": batch.id, "duplicate_file": True, "accepted": 0, "rejected": 0, "unresolved": 0}
    rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig")))); accepted = unresolved = rejected = 0
    for row in rows:
        keyword = (row.get("Keyword") or row.get("keyword") or "").strip(); url = (row.get("URL") or row.get("url") or "").strip()
        entity = _resolve_candidate(db, project_id, keyword, row, batch) if keyword else None
        if entity is None: unresolved += 1; continue
        resolved_city = db.get(City, entity.city_id)
        location = row.get("Location") or (f"{resolved_city.name}, {resolved_city.state_code}" if resolved_city else "")
        def number(*names):
            for name in names:
                if row.get(name) not in (None, ""):
                    try: return float(str(row[name]).replace(",", ""))
                    except ValueError: return None
            return None
        kd = number("KD", "Keyword Difficulty")
        if kd is not None:
            evidence = KeywordDifficultyEvidence(candidate_entity_id=entity.id, keyword=keyword, location_name=location, provider="moz_csv", source_kind="moz_csv", difficulty=kd, raw_payload=row, request_metadata={"import_batch_id": batch.id}, fetched_at=_utc_now(), fresh_until=_utc_now()+timedelta(days=30)); db.add(evidence); db.flush()
            for key_provider in ("mock", "keywords_everywhere_csv"):
                db.add(ProviderCache(cache_key=provider_cache_key(key_provider, "keyword_difficulty", keyword=keyword, location=location, language="en", country="US"), provider="moz_csv", operation="keyword_difficulty", evidence_type="keyword_difficulty", evidence_id=evidence.id, fetched_at=evidence.fetched_at, fresh_until=evidence.fresh_until))
        da = number("DA", "Domain Authority"); pa = number("PA", "Page Authority")
        if da is not None or pa is not None:
            target = url or row.get("Domain") or keyword
            ev = AuthorityEvidence(candidate_entity_id=entity.id, target_url=target, root_domain=row.get("Domain") or target, target_type="URL" if url else "DOMAIN", provider="moz_csv", source_kind="moz_csv", da=da, pa=pa, spam_score=number("Spam Score", "SpamScore"), linking_root_domains=int(number("Linking Root Domains", "Linking Domains") or 0), backlinks=int(number("Backlinks") or 0), raw_payload=row, request_metadata={"import_batch_id": batch.id}, fetched_at=_utc_now(), fresh_until=_utc_now()+timedelta(days=30)); db.add(ev); db.flush()
            authority_key = provider_cache_key("mock", "authority", target_url=target, root_domain=row.get("Domain") or target, target_type="URL" if url else "DOMAIN")
            db.add(ProviderCache(cache_key=authority_key, provider="moz_csv", operation="authority", evidence_type="authority", evidence_id=ev.id, fetched_at=ev.fetched_at, fresh_until=ev.fresh_until))
        accepted += 1
    batch.row_count = len(rows); batch.accepted_count = accepted; batch.rejected_count = rejected; report = dict(batch.error_summary or {}); report["unresolved_count"] = unresolved; batch.error_summary = report; db.commit()
    return {"import_batch_id": batch.id, "duplicate_file": False, "accepted": accepted, "rejected": rejected, "unresolved": unresolved}


def import_manual_evidence(db: Session, project_id: str, row: dict):
    batch, _ = _batch(db, project_id, "manual", "manual-entry", repr(sorted(row.items())).encode())
    keyword = (row.get("keyword") or "").strip(); entity = _resolve_candidate(db, project_id, keyword, row, batch)
    if entity is None: batch.rejected_count = 1; db.commit(); return {"import_batch_id": batch.id, "accepted": 0, "unresolved": 1}
    value = float(row["value"]); metric = row.get("metric_type")
    if metric == "search_volume": db.add(SearchVolumeEvidence(candidate_entity_id=entity.id, keyword=keyword, provider="manual", source_kind="manual", avg_monthly_searches=int(value), raw_payload=row, request_metadata={"note": row.get("note")}, fetched_at=_utc_now()))
    elif metric == "keyword_difficulty": db.add(KeywordDifficultyEvidence(candidate_entity_id=entity.id, keyword=keyword, provider="manual", source_kind="manual", difficulty=value, raw_payload=row, request_metadata={"note": row.get("note")}, fetched_at=_utc_now()))
    else: raise ValueError("Unsupported manual metric type")
    batch.row_count = batch.accepted_count = 1; db.commit(); return {"import_batch_id": batch.id, "accepted": 1, "unresolved": 0}
