"""
FastAPI lifespan manager - the startup/shutdown hooks that run once when
the app process starts and stops, as opposed to per-request dependencies.

Kept in its own module rather than inline in main.py: main.py's job is app
wiring (middleware, static files, router registration), and startup/shutdown
behavior is easier to find, read, and unit-test in isolation from all of
that. This is FastAPI's own documented pattern - an async generator wrapped
in `@asynccontextmanager`, taking the `FastAPI` app instance, with a single
`yield` splitting startup code (before) from shutdown code (after).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db
from app.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    start_scheduler()
    yield
    stop_scheduler()
