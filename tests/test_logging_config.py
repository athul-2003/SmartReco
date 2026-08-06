import logging

import pytest

from app.config import Settings
from app.logging_config import configure_logging


@pytest.fixture
def _restore_root_logging():
    # configure_logging() mutates the global root logger (that's the whole
    # point), so tests must restore it afterward - otherwise a test running
    # later in the same session could inherit whatever handlers/level this
    # test left behind, including stripping pytest's own log-capture handler.
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    yield
    root.handlers[:] = original_handlers
    root.setLevel(original_level)


def test_configure_logging_applies_level_from_settings(_restore_root_logging):
    configure_logging(Settings(log_level="DEBUG"))
    assert logging.getLogger().level == logging.DEBUG


def test_configure_logging_defaults_to_info(_restore_root_logging):
    configure_logging(Settings())
    assert logging.getLogger().level == logging.INFO


def test_configure_logging_installs_a_formatted_handler(_restore_root_logging):
    configure_logging(Settings())
    root = logging.getLogger()
    assert root.handlers
    assert root.handlers[0].formatter is not None
