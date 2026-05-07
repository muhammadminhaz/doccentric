import os
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.core.config import (
    DOCENTRIC_AUTO_DB_CREATE,
    DOCENTRIC_OTEL_ENABLED,
    DOCENTRIC_REQUEST_LOGGING,
    DOCENTRIC_SEED_DATA,
    DOCENTRIC_SKIP_DB_INIT,
)
from app.core.database import engine, Base
from app.core.logging import setup_logging
from app.core.middleware import RequestContextMiddleware
from app.core.observability import setup_observability
from app.core.seed import seed_dummy_doctor
from app.api import patients, audio
from app.api.routes import visits

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if DOCENTRIC_OTEL_ENABLED == "1":
        setup_observability(app, sqlalchemy_engine=engine)
    # Opt-in schema creation to avoid long startup hangs if DB isn't reachable.
    if DOCENTRIC_AUTO_DB_CREATE == "1" and not (DOCENTRIC_SKIP_DB_INIT == "1" or os.getenv("PYTEST_CURRENT_TEST")):
        try:
            Base.metadata.create_all(bind=engine)
        except Exception:
            import logging

            logging.getLogger(__name__).exception("db_init_failed")
        else:
            if DOCENTRIC_SEED_DATA == "1":
                try:
                    from app.core.database import SessionLocal

                    db = SessionLocal()
                    try:
                        seed_dummy_doctor(db)
                    finally:
                        db.close()
                except Exception:
                    import logging

                    logging.getLogger(__name__).exception("seed_failed")
    yield


app = FastAPI(
    title="DocCentric API",
    description="AI-powered patient management system",
    lifespan=lifespan
)

if DOCENTRIC_REQUEST_LOGGING != "0":
    app.add_middleware(RequestContextMiddleware)

app.include_router(patients.router, prefix="/api", tags=["patients"])
app.include_router(audio.router, prefix="/api", tags=["audio"])
app.include_router(visits.router, tags=["visits"])


@app.get("/")
async def root():
    return {"message": "DocCentric API", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
