"""
Manually triggers the daily digest job on demand. Run via `make digest`.

Runs the exact same app.services.digest.run_daily_digest() the real
APScheduler cron job calls (see app/scheduler.py) - this exists so the
bonus can be seen working without waiting for its 08:00 trigger, or
restarting the app to change it.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session

from app.db import engine
from app.services.digest import run_daily_digest


def _configure_clean_console_logging() -> None:
    """Deliberately narrower than app.logging_config.configure_logging():
    this is a one-shot CLI command, not the running app, so a person
    watching the terminal shouldn't see every httpx/Mesh/Qdrant request or
    internal agent step - only run_daily_digest()'s own per-user progress
    line, which is what actually tells them this is working, not stuck.
    Everything else (httpx, agent.graph, etc.) stays at WARNING - silent
    unless something's actually wrong."""
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    logging.getLogger("app.services.digest").setLevel(logging.INFO)


def main() -> None:
    _configure_clean_console_logging()
    with Session(engine) as session:
        sent = run_daily_digest(session)
        print(f"digests sent: {sent}")


if __name__ == "__main__":
    main()
