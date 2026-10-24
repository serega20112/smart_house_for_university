"""Общие помощники отображения, нужные каждому мапперу."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Table

from backend.infrastructure.database.models import Base


def row_values(table: Table, row: Base) -> dict[str, object]:
    """Возвращает значения колонок строки простым словарём.

    Хранилища пишут запросами Core, а не через объект сессионного графа, поэтому
    отображённый экземпляр сначала надо разгладить. Держится это здесь, чтобы ни одно
    хранилище не знало, какие колонки случайно есть у таблицы.

    Args:
        table: Таблица, к которой относится строка.
        row: Строка для разглаживания.

    Returns:
        dict[str, object]: Имя колонки с её значением.
    """
    return {column.name: getattr(row, column.name) for column in table.columns}


def as_utc(value: datetime | None) -> datetime | None:
    """Возвращает момент в часовом поясе UTC или None, если значения нет."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def parse_uuid(raw: str | UUID) -> UUID:
    """Разбирает значение UUID, падая на всём, что UUID не является."""
    if isinstance(raw, UUID):
        return raw
    return UUID(str(raw))
