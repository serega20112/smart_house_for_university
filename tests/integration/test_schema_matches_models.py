"""ORM-модели сверяются с реальной схемой: ни лишней, ни недостающей колонки.

Правда о схеме живёт в миграциях, а правде о полях — в моделях и мапперах; пока их не
сверять, расхождение всплывает только в проде, как это сделал фантомный `version` в
P0-1. Этот тест подключается к настоящей PostgreSQL (если она поднята) и проверяет, что
каждая таблица из метаданных существует и её колонки ровно совпадают с колонками в базе.
"""

from __future__ import annotations

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from backend.config.settings import Settings
from backend.infrastructure.database.models import Base


def _drift(connection: Connection) -> list[str]:
    """Сравнивает метаданные моделей с фактической схемой базы.

    Args:
        connection: Синхронное соединение внутри асинхронного.

    Returns:
        list[str]: Описания расхождений; пусто, когда схема и модели совпадают.
    """
    inspector = inspect(connection)
    existing = set(inspector.get_table_names())
    problems: list[str] = []
    for table in Base.metadata.sorted_tables:
        if table.name not in existing:
            problems.append(f"table {table.name!r} is missing from the database")
            continue
        actual = {column["name"] for column in inspector.get_columns(table.name)}
        expected = {column.name for column in table.columns}
        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            problems.append(f"table {table.name!r} columns differ: missing={missing} extra={extra}")
    return problems


async def test_orm_models_match_migrated_schema() -> None:
    """Каждая ORM-модель имеет ровно те колонки, что развёрнуты миграциями.

    Returns:
        None: Только проверка совпадения моделей и схемы.
    """
    engine = create_async_engine(Settings().database_url)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
            problems = await connection.run_sync(_drift)
    except Exception as error:
        pytest.skip(f"PostgreSQL not reachable for schema check: {error}")
    finally:
        await engine.dispose()

    assert problems == []
