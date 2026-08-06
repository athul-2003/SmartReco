"""
FastAPI lifespan manager - the startup/shutdown hooks that run once when
the app process starts and stops, as opposed to per-request dependencies.

Kept in its own module rather than inline in main.py: main.py's job is app
wiring (middleware, static files, router registration), and startup/shutdown
behavior is easier to find, read, and unit-test in isolation from all of
that. This is FastAPI's own documented pattern - an async generator wrapped
in `@asynccontextmanager`, taking the `FastAPI` app instance, with a single
`yield` splitting startup code (before) from shutdown code (after).

Every startup-time side effect lives here, not scattered across module
import time elsewhere - configure_langsmith() used to run at import time in
main.py, which meant it ran the instant anything imported `app.main`
(including every test, via conftest.py), not specifically "when the app
actually starts". Consolidating it into the startup phase alongside
init_db()/start_scheduler() makes "when does app startup happen" a single,
unambiguous answer.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.db import init_db
from app.observability import configure_langsmith
from app.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_langsmith(get_settings())
    init_db()
    start_scheduler()
    yield
    stop_scheduler()
