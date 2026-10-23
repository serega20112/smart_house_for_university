"""Разбор сырых ответов Redis в питоновские значения.

Сервер отвечает то байтами, то строками, то JSON внутри поля хеша, и эта
неоднородность — деталь транспорта, а не домена: везде ниже этих функций живут
обычные строки, числа и даты.
"""

from __future__ import annotations

import json
from datetime import datetime


def as_text(raw: bytes | str | None) -> str | None:
    """Превращает ответ сервера в текст, оставляя None на месте."""
    if raw is None:
        return None
    return raw.decode("utf-8") if isinstance(raw, bytes) else raw


def loads(raw: str | bytes | None, fallback: dict[str, str]) -> dict[str, str]:
    """Разбирает JSON словаря из поля хеша, возвращая запасной вариант при пустоте."""
    if not raw:
        return fallback
    decoded = json.loads(as_text(raw) or "")
    return decoded if isinstance(decoded, dict) else fallback


def as_float(raw: str | None) -> float | None:
    """Превращает значение поля в число или None."""
    return None if raw is None else float(raw)


def as_datetime(raw: str | None) -> datetime | None:
    """Превращает ISO-метку времени в дату или None."""
    return None if raw is None else datetime.fromisoformat(raw)
