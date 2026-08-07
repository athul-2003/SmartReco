import pytest

from app import scheduler
from app.config import Settings


@pytest.fixture(autouse=True)
def _isolated_scheduler_settings(tmp_path, monkeypatch):
    """scheduler.py's persistent job store is built from
    get_settings().database_url, not the per-test `session` fixture
    (there's no HTTP request/session-dependency involved in starting a
    scheduler) - point it at a throwaway file-based SQLite DB unique to
    this test, so these tests never touch the real on-disk DB file. A real
    file (not `sqlite://` in-memory) is used deliberately: two separate
    in-memory connections don't share data, which would silently defeat
    the restart-persistence test below."""
    db_path = tmp_path / "test_scheduler.db"
    test_settings = Settings(database_url=f"sqlite:///{db_path}")
    monkeypatch.setattr(scheduler, "get_settings", lambda: test_settings)


def test_start_scheduler_registers_daily_digest_job():
    sched = scheduler.start_scheduler()
    try:
        job = sched.get_job(scheduler.DIGEST_JOB_ID)
        assert job is not None
    finally:
        scheduler.stop_scheduler()


def test_start_scheduler_is_idempotent():
    first = scheduler.start_scheduler()
    try:
        second = scheduler.start_scheduler()
        assert first is second
    finally:
        scheduler.stop_scheduler()


def test_stop_scheduler_without_start_is_a_noop():
    scheduler.stop_scheduler()


def test_digest_job_has_a_generous_misfire_grace_time():
    # APScheduler's own default is a mere 1 second - too short to catch a
    # process that was down for any real stretch (laptop asleep, container
    # stopped). This is what actually lets a late run still fire, on top of
    # the persistent job store below remembering it was due at all.
    sched = scheduler.start_scheduler()
    try:
        job = sched.get_job(scheduler.DIGEST_JOB_ID)
        assert job.misfire_grace_time == scheduler.MISFIRE_GRACE_SECONDS
        assert job.misfire_grace_time > 1
    finally:
        scheduler.stop_scheduler()


def test_scheduler_survives_restart_without_crashing_on_persisted_job():
    # Regression test for the real breaking-change risk of adding
    # persistence: APScheduler's add_job() defaults to
    # replace_existing=False, so re-adding the same job id to a store that
    # already has it (i.e. every restart, once the store is persistent)
    # raises ConflictingIdError unless replace_existing=True is set.
    # stop_scheduler() clears the cached instance, so the next
    # start_scheduler() below builds a fresh BackgroundScheduler against
    # the same underlying (patched) DB file - exactly what a real process
    # restart against the same DB looks like.
    scheduler.start_scheduler()
    scheduler.stop_scheduler()

    sched = scheduler.start_scheduler()
    try:
        job = sched.get_job(scheduler.DIGEST_JOB_ID)
        assert job is not None
    finally:
        scheduler.stop_scheduler()
