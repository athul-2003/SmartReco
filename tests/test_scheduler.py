from app import scheduler


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
