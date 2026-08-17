import logging
from pathlib import Path
from sqlalchemy import text
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.base import Base
from app.db.session import engine
from app.api.routes import router
from app.api.auth_routes import router as auth_router
from app.core.config import PROJECT_ROOT, get_settings

logger = logging.getLogger("nicheforge.runtime")
settings = get_settings()
if settings.nicheforge_database_url.startswith("sqlite:///"):
    database_path = Path(settings.nicheforge_database_url.removeprefix("sqlite:///"))
    expected_root_db = (PROJECT_ROOT / "nicheforge.db").resolve()
    if database_path.resolve() == (PROJECT_ROOT / "backend" / "nicheforge.db").resolve() and expected_root_db.exists():
        raise RuntimeError(f"Unsafe SQLite runtime path: {database_path}; expected {expected_root_db}")
    logger.warning("database_type=sqlite database_path=%s", database_path.resolve())
else:
    logger.warning("database_type=non-sqlite")

Base.metadata.create_all(bind=engine)
try:
    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version ORDER BY version_num")).scalars().all()
    logger.warning("alembic_revision=%s", ",".join(revision) if revision else "UNSET")
except Exception as exc:
    logger.warning("alembic_revision=UNAVAILABLE reason=%s", type(exc).__name__)

app = FastAPI(title="NicheForge API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Authorization"],
)
app.include_router(router)
app.include_router(auth_router)


@app.get("/health/live")
def live():
    return {"status": "ok"}
