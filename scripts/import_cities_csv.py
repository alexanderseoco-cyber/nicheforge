"""Import a normalized city CSV with columns: name,state_code,population,population_vintage,census_geo_id(optional)."""
import csv, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.db.session import SessionLocal, engine
from app.db.base import Base
from app.models.entities import City

Base.metadata.create_all(bind=engine)
path = Path(sys.argv[1])
with path.open(newline="", encoding="utf-8-sig") as f, SessionLocal() as db:
    for row in csv.DictReader(f):
        db.add(City(
            name=row["name"].strip(), state_code=row["state_code"].strip().upper(),
            population=int(row["population"]), population_vintage=row.get("population_vintage") or "import",
            census_geo_id=row.get("census_geo_id") or None,
        ))
    db.commit()
print("Imported", path)
