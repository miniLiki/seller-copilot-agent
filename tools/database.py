from __future__ import annotations

import os
from collections.abc import Generator

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv()

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
except ImportError:  # Keeps mock-first mode importable before optional DB deps are installed.
    create_engine = None
    DeclarativeBase = object  # type: ignore[assignment]
    Session = object  # type: ignore[assignment]
    sessionmaker = None


def normalize_database_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/seller_copilot")
SQLALCHEMY_DATABASE_URL = normalize_database_url(DATABASE_URL)


class Base(DeclarativeBase):  # type: ignore[misc, valid-type]
    pass


engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True) if create_engine else None
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False) if sessionmaker and engine else None


def get_db() -> Generator[Session, None, None]:
    if SessionLocal is None:
        raise RuntimeError("SQLAlchemy is not installed. Install requirements.txt to use PostgreSQL mode.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
