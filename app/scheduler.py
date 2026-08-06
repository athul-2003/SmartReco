"""
Phase 6 bonus (FR-6): in-process daily job that runs the digest pipeline
(services/digest.py) for every active user. Uses APScheduler's
BackgroundScheduler (its own thread, not asyncio) since the whole
recommendation pipeline underneath is synchronous (sync SQLModel session,
sync Mesh/Qdrant calls) - matches the project's existing sync-everywhere
decision (see docs/BUILD_PLAN.md, Phase 1).
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session

from app.db import engine
from app.services.digest import run_daily_digest

logger = logging.getLogger(__name__)

DIGEST_JOB_ID = "daily_digest"
DIGEST_HOUR = 8  # 08:00 server time, once daily

_scheduler: BackgroundScheduler | None = None


def _run_digest_job() -> None:
    with Session(engine) as session:
        sent = run_daily_digest(session)
        logger.info("Daily digest job complete: %d email(s) sent", sent)


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        _run_digest_job, "cron", hour=DIGEST_HOUR, minute=0, id=DIGEST_JOB_ID
    )
    _scheduler.start()
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
