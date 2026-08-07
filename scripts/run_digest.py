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

from app.db import engine
from app.services.digest import run_daily_digest


def main() -> None:
    with Session(engine) as session:
        sent = run_daily_digest(session)
        print(f"digests sent: {sent}")


if __name__ == "__main__":
    main()
