import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.database import init_db, engine, Base
from app.api import patients, audio


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Database connection failed: {e}")
        print("API will run but database features will be unavailable")
    yield


app = FastAPI(
    title="DocCentric API",
    description="AI-powered patient management system",
    lifespan=lifespan
)

app.include_router(patients.router, prefix="/api", tags=["patients"])
app.include_router(audio.router, prefix="/api", tags=["audio"])


@app.get("/")
async def root():
    return {"message": "DocCentric API", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}