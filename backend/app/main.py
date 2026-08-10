from fastapi import FastAPI
from app.db.base import Base
from app.db.session import engine
from app.api.routes import router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="NicheForge API", version="0.1.0")
app.include_router(router)


@app.get("/health/live")
def live():
    return {"status": "ok"}
