"""
Centralized logging setup - the one place that configures format/level for
every `logging.getLogger(__name__)` call in the app. Individual modules keep
their own per-module logger (the standard, correct pattern - it's what makes
a log line show which module actually produced it); only the one-time setup
of *how* those logs are formatted and *which* levels get through is
centralized here, called once from lifespan.py's startup phase, the same
pattern already used for configure_langsmith().

Without this, logging fell back to Python's bare defaults: no timestamps, no
handler configured, and a silent WARNING floor that would drop any
`logger.info(...)` call without any indication why.
"""

import logging

from app.config import Settings

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


def configure_logging(settings: Settings) -> None:
    # force=True: logging.basicConfig() is a no-op after the first call in a
    # process unless forced - relevant here since tests/reloads can trigger
    # this more than once.
    logging.basicConfig(level=settings.log_level, format=LOG_FORMAT, force=True)
