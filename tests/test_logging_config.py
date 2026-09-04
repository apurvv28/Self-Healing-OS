"""Tests for shared logging configuration."""

from common.logging_config import get_logger, setup_logging


def test_get_logger_returns_named_logger():
    logger = get_logger("test.module")
    assert logger.name == "test.module"


def test_setup_logging_does_not_raise():
    setup_logging(level="DEBUG")
    logger = get_logger(__name__)
    logger.debug("setup_logging test message")
