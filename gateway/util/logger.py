# gateway/util/logger.py
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from gateway.config.settings import settings

# Optional: capture warnings.* into logging
logging.captureWarnings(True)


class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[37m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[41m",
    }
    RESET = "\033[0m"

    def format(self, record):
        # Keep plain levelname for files; only colorize for console
        if getattr(record, "_colorize", False):
            lvl = record.levelname
            record.levelname = f"{self.COLORS.get(lvl, self.RESET)}{lvl}{self.RESET}"
        return super().format(record)


def init_logger() -> logging.Logger:
    """
    Idempotent logger init:
    - Always logs to stdout (Railway captures this).
    - Writes to logs/app.log only in dev.
    - Respects LOG_LEVEL env via settings.log_level.
    """
    root = logging.getLogger()
    if getattr(root, "_ai_clinical_inited", False):
        return logging.getLogger("grader.service")

    # Base level
    level = getattr(logging, (settings.log_level or "INFO").upper(), logging.INFO)
    root.setLevel(level)

    # Clear any default handlers to avoid duplicates
    for h in list(root.handlers):
        root.removeHandler(h)

    # Formatters
    text_fmt = "%(asctime)s %(levelname)s %(name)s - %(message)s"
    date_fmt = "%Y-%m-%dT%H:%M:%S%z"
    plain = logging.Formatter(text_fmt, datefmt=date_fmt)
    colored = ColoredFormatter(text_fmt, datefmt=date_fmt)

    # Console handler -> stdout (visible in Railway)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(colored)

    # Tag console records to colorize levelname, leave files plain
    old_emit = ch.emit

    def emit_with_flag(record):
        record._colorize = True
        return old_emit(record)

    ch.emit = emit_with_flag  # type: ignore[attr-defined]

    root.addHandler(ch)

    # File handler only in dev (containers are ephemeral)
    if (os.getenv("APP_ENV", "dev")).lower() == "dev":
        os.makedirs("logs", exist_ok=True)
        fh = RotatingFileHandler(
            "logs/app.log", maxBytes=50 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        fh.setLevel(level)
        fh.setFormatter(plain)
        root.addHandler(fh)

    # Tame noisy libs if desired
    logging.getLogger("grpc").setLevel(logging.WARNING)

    root._ai_clinical_inited = True  # mark as initialized
    return logging.getLogger("grader.service")
