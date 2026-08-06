from sqlalchemy import inspect
from sqlmodel import create_engine

from app.db import init_db


def test_init_db_creates_every_table(monkeypatch):
    # A fresh engine, isolated from the shared app.db.engine - verifies
    # init_db()'s actual contract (a full, correct schema) end to end.
    # Can't fully isolate this from *other* tests already having imported
    # every model into the process-wide SQLModel.metadata by the time this
    # runs - but init_db() itself importing app.models (see app/db.py)
    # means this holds even for a standalone script that only imports one
    # model directly, e.g. scripts/seed_catalog.py only importing Product.
    fresh_engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    monkeypatch.setattr("app.db.engine", fresh_engine)

    init_db()

    table_names = set(inspect(fresh_engine).get_table_names())
    assert {"users", "products", "events", "recommendations"} <= table_names
