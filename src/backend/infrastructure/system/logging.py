"""Структурированный журнал всего процесса.

Каждый модуль берёт свой журнал через :func:`get_logger` — это привязанный логгер
``structlog``. Контекст передают именованными аргументами
(``log.info("board.online", board_id=..., user_id=...)``), и он рисуется в той же строке, что
и событие: словарь ``extra={"ctx": {...}}``, который каждое место вызования собирало руками,
больше не нужен.

Записи остаются машиночитаемыми и свободными от персональных данных: пишут только имена
устройств, номера каналов и технические идентификаторы.
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
    """Настраивает structlog и мост стандартной библиотеки один раз на процесс.

    Дерево журналирования стандартной библиотеки тоже заводят в structlog, поэтому
    запись от SQLAlchemy, ARQ или библиотеки Telegram рисуется тем же конвейером, а не
    голой строкой посреди потока JSON.

    Вызвать функцию дважды безопасно: второй раз оставляет первую настройку, поэтому за
    ней могут прийти и тест, и композиционный корень.

    Args:
        level: Минимальный уровень, с которым рисуют всякую запись.
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
    """Возвращает структурированный журнал пространства имён приложения.

    Args:
        name: Имя модуля или компонента, добавляемое к пространству имён приложения.

    Returns:
        structlog.stdlib.BoundLogger: Журнал, принимающий контекст именованными
            аргументами.
    """
    qualified = f"{LOGGER_ROOT}.{name}" if name else LOGGER_ROOT
    return structlog.get_logger(qualified)
