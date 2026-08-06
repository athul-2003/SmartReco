import pytest
from fastapi import FastAPI

from app import lifespan as lifespan_module


@pytest.mark.anyio
async def test_lifespan_runs_startup_before_yield_and_shutdown_after(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(lifespan_module, "init_db", lambda: calls.append("init_db"))
    monkeypatch.setattr(
        lifespan_module, "start_scheduler", lambda: calls.append("start_scheduler")
    )
    monkeypatch.setattr(
        lifespan_module, "stop_scheduler", lambda: calls.append("stop_scheduler")
    )

    app = FastAPI()
    async with lifespan_module.lifespan(app):
        # Startup already ran by the time we're inside the context.
        assert calls == ["init_db", "start_scheduler"]

    # Shutdown runs on exiting the context.
    assert calls == ["init_db", "start_scheduler", "stop_scheduler"]


@pytest.fixture
def anyio_backend():
    return "asyncio"
