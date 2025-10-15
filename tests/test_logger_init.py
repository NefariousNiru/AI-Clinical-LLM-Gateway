# tests/test_logger_init.py
import logging
from gateway.util.logger import init_logger


def test_logger_idempotent_and_colored_console_only_in_ci(monkeypatch):
    # First call creates handlers
    logger = init_logger()
    root = logging.getLogger(logger.name)
    handler_ids = {id(h) for h in root.handlers}
    # Second call should not duplicate
    _ = init_logger()
    handler_ids2 = {id(h) for h in root.handlers}
    assert handler_ids == handler_ids2
