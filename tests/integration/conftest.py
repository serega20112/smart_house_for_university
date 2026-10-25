"""Фикстуры интеграционных тестов, которым нужна настоящая PostgreSQL.

Тесты ниже идут к реальной базе и откатывают свою транзакцию, поэтому не оставляют
посторонних строк между прогонами. Если база недоступна (локальная машина без поднятого
стенда), проверка пропускается, а не падает: отсутствие сервиса — не дефект кода.

Соединение с открытой транзакцией живёт отдельной фикстурой: чтения системы идут через
фабрику сессий, и ей нужен тот же откатываемый коннект, а не второй, независимый.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.config.settings import Settings


@pytest_asyncio.fixture
async def sql_connection() -> AsyncIterator[AsyncConnection]:
    """Соединение с открытой и всегда откатываемой транзакцией.

    Yields:
        AsyncConnection: Соединение, все изменения на котором откатятся по выходе.
    """
    settings = Settings()
    engine = create_async_engine(settings.database_url)
    probe = text("SELECT 1 FROM users LIMIT 0")
    try:
        async with engine.connect() as connection:
            await connection.execute(probe)
    except Exception as error:
        await engine.dispose()
        pytest.skip(f"PostgreSQL not reachable for integration tests: {error}")

    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            yield connection
        finally:
            await transaction.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def sql_session(sql_connection: AsyncConnection) -> AsyncIterator[AsyncSession]:
    """Сессия поверх откатываемого соединения.

    Args:
        sql_connection: Соединение теста с открытой транзакцией.

    Yields:
        AsyncSession: Сессия, чьи записи откатятся по выходе из теста.
    """
    session = AsyncSession(bind=sql_connection, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()


@pytest_asyncio.fixture
def sql_session_factory(sql_connection: AsyncConnection) -> async_sessionmaker[AsyncSession]:
    """Фабрика сессий на том же откатываемом соединении.

    Нужна чтениям, которые открывают сессию сами: они видят незафиксированные строки
    теста и так же откатываются вместе с его транзакцией.

    Args:
        sql_connection: Соединение теста с открытой транзакцией.

    Returns:
        async_sessionmaker[AsyncSession]: Фабрика, открывающая сессию на соединении.
    """
    return async_sessionmaker(bind=sql_connection, expire_on_commit=False)
