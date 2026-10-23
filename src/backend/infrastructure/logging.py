"""Structured logging for the whole process.

Every module obtains its logger through :func:`get_logger`, which returns a
``structlog`` bound logger. Context is passed as keyword arguments
(``log.info("board.online", board_id=..., user_id=...)``) and is rendered into the
same line as the event, which removes the ``extra={"ctx": {...}}`` dictionary
every call site used to build by hand.

Records stay machine readable and free of personal data: only device names,
channel numbers and technical identifiers are ever written.
"""

from __future__ import annotations

import logging
import sys
from typing import Final

import structlog
from structlog.typing import Processor

LOGGER_ROOT: Final = "backend"

_SHARED_PROCESSORS: Final[tuple[Processor, ...]] = (
    structlog.contextvars.merge_contextvars,
    structlog.processors.add_log_level,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
)

_configured = False


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog and the standard library bridge once per process.

    The standard library logging tree is routed into structlog as well, so a
    record produced by SQLAlchemy, ARQ or the Telegram library is rendered with
    the same pipeline as one produced by this application instead of appearing as
    a bare string in the middle of the JSON stream.

    Calling the function twice is harmless: the second call keeps the first
    configuration, which lets a test and a composition root both ask for it.

    Args:
        level: Minimum level every record is rendered at.

    Returns:
        None.
    """
    global _configured
    if _configured:
        return

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(numeric_level)

    structlog.configure(
        processors=[
            *_SHARED_PROCESSORS,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    logging.getLogger(LOGGER_ROOT).setLevel(numeric_level)
    _configured = True


def get_logger(name: str = "") -> structlog.stdlib.BoundLogger:
    """Return a structured logger of the application namespace.

    Args:
        name: Module or component name, appended to the namespace of the
            application.

    Returns:
        structlog.stdlib.BoundLogger: Logger accepting keyword context.
    """
    qualified = f"{LOGGER_ROOT}.{name}" if name else LOGGER_ROOT
    return structlog.get_logger(qualified)
