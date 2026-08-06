from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.db import init_db
from app.observability import configure_langsmith
from app.routers import admin, auth, catalog, events, pages, recommendations
from app.scheduler import start_scheduler, stop_scheduler

settings = get_settings()
configure_langsmith(settings)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="SmartReco", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(admin.router)
app.include_router(recommendations.router)
app.include_router(events.router)
