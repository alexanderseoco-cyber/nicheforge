from datetime import date, datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db.base import Base
from app.models.entities import FxRateEvidence
from app.services.currency_normalization import FxRate
from app.services.fx_evidence import persist_fx_rate, resolve_persisted_fx

def test_latest_fx_survives_fresh_service_resolution():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        persist_fx_rate(db, FxRate("PKR", "USD", 0.003599, "2026-08-14", "exchangerate_api_open"))
    with Session(engine) as fresh_db:
        restored = resolve_persisted_fx(fresh_db, "PKR", "USD", now=datetime.utcnow())
    assert restored is not None
    assert restored.rate == 0.003599
    assert restored.rate_date == "2026-08-14"

def test_latest_does_not_satisfy_historical_date():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        persist_fx_rate(db, FxRate("PKR", "USD", 0.003599, "2026-08-14", "exchangerate_api_open"))
        assert resolve_persisted_fx(db, "PKR", "USD", mode="historical", as_of=date(2026, 8, 10)) is None
