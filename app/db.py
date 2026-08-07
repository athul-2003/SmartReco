from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

settings = get_settings()


def sqlite_connect_args(database_url: str) -> dict:
    """check_same_thread=False is needed for any multi-threaded access to a
    SQLite connection (FastAPI's threadpool, APScheduler's own background
    thread in scheduler.py) - not a valid connect arg for other drivers
    (e.g. psycopg2), so this is conditional on the URL scheme rather than
    always applied."""
    return {"check_same_thread": False} if database_url.startswith("sqlite") else {}


engine = create_engine(
    settings.database_url, connect_args=sqlite_connect_args(settings.database_url)
)


def init_db() -> None:
    import app.models  # noqa: F401 - registers every table on SQLModel.metadata before create_all

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
