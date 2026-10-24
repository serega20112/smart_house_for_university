"""Приёмы, общие для всех SQL-репозиториев.

Реализация портов хранилищ отличается таблицей, типом строки, типом агрегата и
маппером между ними; способ прочитать строку, вставить пачку или отличить
уникальный конфликт от прочего — один на всех, и он здесь.

Границу транзакции владеет единица работы: ни один приём ниже ни commit'ит, ни
откатывает.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy import ColumnElement, Table, insert, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import CursorResult, Result
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from backend.infrastructure.database.mappers import row_values
from backend.infrastructure.database.models import Base

Runner = AsyncConnection | AsyncSession
UNIQUE_VIOLATION = "23505"


def is_unique_violation(error: IntegrityError) -> bool:
    """Уникальное ли ограничение нарушил отказ хранилища.

    Класс SQL-состояния — единственная часть отказа, одинаковая для разных
    драйверов, поэтому разбор перевода смотрит только на неё.

    Args:
        error: Отказ, который вернуло хранилище.

    Returns:
        bool: True, когда хранилище отвергло дубликат значения.
    """
    return getattr(error.orig, "sqlstate", None) == UNIQUE_VIOLATION


async def first_row[Row: Base](
    runner: Runner, model: type[Row], *criteria: ColumnElement[bool]
) -> Row | None:
    """Одиночная строка выборки или None."""
    result = await runner.execute(select(model).where(*criteria))
    return result.scalar_one_or_none()


async def every_row[Row: Base](
    runner: Runner, model: type[Row], *criteria: ColumnElement[bool]
) -> list[Row]:
    """Все строки выборки."""
    result = await runner.execute(select(model).where(*criteria))
    return list(result.scalars().all())


def affected_rows(result: Result[Any]) -> int:
    """Возвращает число строк, изменённых командой записи.

    `execute` возвращает широкой `Result`, у которого `rowcount` не объявлен, хотя для
    команды изменения хранилище всегда отдаёт `CursorResult` с этим числом. Приведение
    сосредоточено здесь одной строкой, чтобы ни один репозиторий не повторял его.

    Args:
        result: Результат, вернувшийся после команды изменения.

    Returns:
        int: Число затронутых строк.
    """
    return cast("CursorResult[Any]", result).rowcount


async def insert_rows[Row: Base](runner: Runner, table: Table, rows: Sequence[Row]) -> None:
    """Пишет несколько строк одной таблицы."""
    if not rows:
        return
    await runner.execute(insert(table), [row_values(table, row) for row in rows])


def upsert_columns(table: Table, *frozen: str) -> dict[str, object]:
    """Возвращает колонки, которые upsert обновляет, когда строка уже есть.

    Args:
        table: Таблица, для которой строится запрос.
        *frozen: Колонки, которых трогать нельзя (ключ и момент создания).

    Returns:
        dict[str, object]: Колонка -> значение из предложенной строки.
    """
    excluded = postgresql.insert(table).excluded
    untouched = set(frozen)
    return {
        column.name: excluded[column.name]
        for column in table.columns
        if column.name not in untouched
    }
