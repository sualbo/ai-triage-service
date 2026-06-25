from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from app.config import settings


def setup_logging() -> logging.Logger:
    settings.ensure_runtime_dirs()

    logger = logging.getLogger("ai_triage_service")
    logger.setLevel(settings.log_level.upper())
    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        settings.log_file,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = setup_logging()
