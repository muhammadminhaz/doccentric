import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/doccentric"
)

connect_args = {}
if DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgresql+"):
    # Avoid long hangs if DB isn't reachable (common in local dev/tests).
    connect_args = {"connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "2"))}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
