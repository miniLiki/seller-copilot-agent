from __future__ import annotations

import os

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from .platform_store import store as mock_store

if load_dotenv:
    load_dotenv()


def build_store():
    if os.getenv("SELLER_COPILOT_STORAGE", "mock").lower() == "postgres":
        from .database import SessionLocal
        from .postgres_store import PostgresStore

        return PostgresStore(SessionLocal)
    return mock_store


store = build_store()
