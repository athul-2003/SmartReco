from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.lifespan import lifespan
from app.routers import router

settings = get_settings()

app = FastAPI(title="SmartReco", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(router)
