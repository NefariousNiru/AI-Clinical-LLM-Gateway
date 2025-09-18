import logging
from logging import Logger
from logging.handlers import RotatingFileHandler
import os
from gateway.config.settings import settings

class ColoredFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[37m",     # White
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[41m",  # Red background
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)

def init_logger() -> Logger:
    os.makedirs("logs", exist_ok=True)
    log_level = getattr(logging, (settings.log_level or "INFO").upper(), logging.INFO)
    log_formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s - %(message)s"
    )
    file_handler = RotatingFileHandler(
        "logs/app.log", maxBytes=50 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(log_formatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ColoredFormatter("%(asctime)s %(levelname)s %(name)s - %(message)s"))
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    logger = logging.getLogger("grader.service")
    return logger

