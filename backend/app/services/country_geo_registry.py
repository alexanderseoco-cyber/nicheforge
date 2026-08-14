"""Import and report validated country geo mappings without provider calls."""
from datetime import datetime
import csv
import io
import zipfile
from app.models.entities import ProviderCountryGeoMapping

def import_country_mappings(db, records: list[dict], *, provider="google_ads", source="official_import"):
    imported = []
    for record in records:
        code = str(record["country_code"]).upper()
        if str(record.get("target_type", "")).upper() != "COUNTRY":
            raise ValueError(f"Country mapping {code} is not target type COUNTRY")
        resource = str(record["resource_name"])
        if not resource.startswith("geoTargetConstants/"):
            raise ValueError(f"Invalid Google geo resource for {code}")
        row = db.query(ProviderCountryGeoMapping).filter_by(country_code=code, provider=provider).one_or_none()
        if row is None:
            row = ProviderCountryGeoMapping(country_code=code, provider=provider)
            db.add(row)
        row.criterion_id = str(record["criterion_id"]); row.resource_name = resource
        row.provider_name = record.get("provider_name"); row.target_type = "COUNTRY"
        row.provider_status = record.get("provider_status"); row.mapping_status = "MAPPED"
        row.fetched_at = datetime.utcnow(); row.provenance = {"source": source, **record.get("provenance", {})}
        imported.append(row)
    db.commit()
    return imported


def import_google_geo_targets_file(db, path, *, source_version: str):
    """Import active Country rows from Google's official CSV or ZIP dataset."""
    path = str(path)
    if path.lower().endswith(".zip"):
        with zipfile.ZipFile(path) as archive:
            names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            if len(names) != 1:
                raise ValueError(f"Expected exactly one CSV in Google geo archive, found {len(names)}")
            text = archive.read(names[0]).decode("utf-8-sig")
    else:
        with open(path, "r", encoding="utf-8-sig", newline="") as handle:
            text = handle.read()
    rows = list(csv.DictReader(io.StringIO(text)))
    accepted = []
    for row in rows:
        if row.get("Target Type", "").strip() != "Country" or row.get("Status", "").strip() != "Active":
            continue
        code = row.get("Country Code", "").strip().upper()
        criterion = row.get("Criteria ID", "").strip()
        if len(code) != 2 or not code.isalpha() or not criterion.isdigit() or int(criterion) <= 0:
            continue
        accepted.append({"country_code": code, "criterion_id": criterion,
            "resource_name": f"geoTargetConstants/{criterion}", "provider_name": row.get("Name"),
            "target_type": "COUNTRY", "provider_status": "Active",
            "provenance": {"source": "google_geo_targets_csv", "source_version": source_version,
                           "canonical_name": row.get("Canonical Name"), "parent_id": row.get("Parent ID")}})
    by_code = {}
    for row in accepted:
        if row["country_code"] in by_code and by_code[row["country_code"]]["criterion_id"] != row["criterion_id"]:
            raise ValueError(f"Ambiguous active country mappings for {row['country_code']}")
        by_code[row["country_code"]] = row
    imported = import_country_mappings(db, list(by_code.values()), source="google_geo_targets_csv")
    return {"raw_rows": len(rows), "active_country_rows": len(accepted), "imported": len(imported), "duplicates_collapsed": len(accepted) - len(by_code), "source_version": source_version}
