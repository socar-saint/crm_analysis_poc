"""Project-wide logging helpers."""

import logging
import os
from typing import Final

_DEFAULT_LOG_FORMAT: Final[str] = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
_ENV_LOG_LEVEL_KEY: Final[str] = "LOG_LEVEL"

_DEFAULT_HANDLER = logging.StreamHandler()


class _State:
    """Module state holder."""

    configured: bool = False


_state = _State()


def _resolve_level(level: int | str | None) -> int:
    """Normalize level values, falling back to INFO when unclear."""

    candidate = level if level is not None else os.getenv(_ENV_LOG_LEVEL_KEY)
    if candidate is None:
        return logging.INFO

    if isinstance(candidate, int):
        return candidate

    text = str(candidate).strip()
    if not text:
        return logging.INFO
    if text.isdigit():
        return int(text)

    maybe_level = getattr(logging, text.upper(), None)
    if isinstance(maybe_level, int):
        return maybe_level

    return logging.INFO


def configure_logging(
    *,
    level: int | str | None = None,
    fmt: str = _DEFAULT_LOG_FORMAT,
    datefmt: str | None = None,
    handler: logging.Handler | None = None,
    force: bool = False,
) -> None:
    """Configure the root logger once so every service shares the same setup."""

    resolved_level = _resolve_level(level)
    formatter = logging.Formatter(fmt, datefmt)

    root_logger = logging.getLogger()
    active_handler = handler or _DEFAULT_HANDLER
    active_handler.setFormatter(formatter)

    if force:
        root_logger.handlers.clear()

    if active_handler not in root_logger.handlers:
        root_logger.addHandler(active_handler)

    root_logger.setLevel(resolved_level)
    _state.configured = True


def get_logger(name: str | None = None, level: int | str | None = None) -> logging.Logger:
    """Return a shared project logger, configuring defaults on the first call."""

    if not _state.configured:
        configure_logging()

    logger_name = name or "agent"
    logger = logging.getLogger(logger_name)

    if level is not None:
        logger.setLevel(_resolve_level(level))

    return logger
