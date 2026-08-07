"""
Manually triggers the daily digest job on demand. Run via `make digest`.

Runs the exact same app.services.digest.run_daily_digest() the real
APScheduler cron job calls (see app/scheduler.py) - this exists so the
bonus can be seen working without waiting for its 08:00 trigger, or
restarting the app to change it.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session

from app.config import get_settings
from app.db import engine
from app.logging_config import configure_logging
from app.services.digest import run_daily_digest


def main() -> None:
    # Without this, run_daily_digest()'s own per-user progress logging goes
    # nowhere - Python's logging module does nothing until configured, and
    # this script (unlike the running app) never otherwise calls
    # configure_logging(). A digest across many users runs a real LangGraph
    # pipeline per user, which takes a few seconds each - without visible
    # progress, a `make digest` run with no console output for a while looks
    # identical to a hung one.
    configure_logging(get_settings())
    with Session(engine) as session:
        sent = run_daily_digest(session)
        print(f"digests sent: {sent}")


if __name__ == "__main__":
    main()
