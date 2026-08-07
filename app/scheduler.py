"""
Phase 6 bonus (FR-6): in-process daily job that runs the digest pipeline
(services/digest.py) for every active user. Uses APScheduler's
BackgroundScheduler (its own thread, not asyncio) since the whole
recommendation pipeline underneath is synchronous (sync SQLModel session,
sync Mesh/Qdrant calls) - matches the project's existing sync-everywhere
decision (see docs/BUILD_PLAN.md, Phase 1).

The job store is persistent (SQLAlchemyJobStore, pointed at the app's own
DB URL) rather than APScheduler's default in-memory one - with an
in-memory store, a missed 08:00 run (process wasn't up yet - laptop
asleep, container stopped, etc.) is just gone the moment the scheduler
restarts, since nothing remembers it was ever due. Persistence plus
misfire_grace_time below lets a late-but-still-recent run actually fire
once the app comes back up, instead of silently skipping straight to
tomorrow.

The job store gets its own engine (via `url=`, not `engine=app.db.engine`)
rather than sharing the app's main engine, deliberately: SQLAlchemyJobStore
calls `engine.dispose()` on shutdown, and stop_scheduler() runs on every
app shutdown - sharing the engine would mean disposing the same connection
pool every other part of the app relies on, as an unrelated side effect.
Same underlying DB file/server either way, just a separate connection.
"""

import logging

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session

from app.config import get_settings
from app.db import engine, sqlite_connect_args
from app.services.digest import run_daily_digest

logger = logging.getLogger(__name__)

DIGEST_JOB_ID = "daily_digest"
DIGEST_HOUR = 8  # 08:00 server time, once daily

# How late a missed 08:00 run is still allowed to fire (needs the
# persistent job store above to matter at all - an in-memory store has
# nothing to check on restart). Long enough to catch a typical "opened my
# laptop a few hours late" gap; short enough not to send a "your morning
# picks" digest deep into the evening on a genuinely stale miss.
MISFIRE_GRACE_SECONDS = 6 * 60 * 60

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
    database_url = get_settings().database_url
    # Must be added before .start() - APScheduler only lazily creates its
    # own default in-memory job store if "default" is still unset by then.
    _scheduler.add_jobstore(
        SQLAlchemyJobStore(
            url=database_url,
            engine_options={"connect_args": sqlite_connect_args(database_url)},
        )
    )
    _scheduler.add_job(
        _run_digest_job,
        "cron",
        hour=DIGEST_HOUR,
        minute=0,
        id=DIGEST_JOB_ID,
        # Both required together, not just one: replace_existing avoids a
        # ConflictingIdError crash on every restart once this job already
        # exists in the persistent store (APScheduler's add_job default is
        # replace_existing=False); misfire_grace_time is what actually
        # lets a late run still fire (APScheduler's own default is a mere
        # 1 second).
        replace_existing=True,
        misfire_grace_time=MISFIRE_GRACE_SECONDS,
    )
    _scheduler.start()
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
