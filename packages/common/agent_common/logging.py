"""Lightweight logging helpers shared by agents."""

from __future__ import annotations

import logging
from typing import Final

_DEFAULT_LOG_FORMAT: Final[str] = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return a configured logger with a consistent format."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_DEFAULT_LOG_FORMAT))
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger
