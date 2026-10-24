"""Фикстуры интеграционных тестов, которым нужна настоящая PostgreSQL.

Тест ниже идёт к реальной базе и откатывает свою транзакцию, поэтому не оставляет
посторонних строк между прогонами. Если база недоступна (локальная машина без поднятого
стенда), проверка пропускается, а не падает: отсутствие сервиса — не дефект кода.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.config.settings import Settings


@pytest_asyncio.fixture
async def sql_session() -> AsyncIterator[AsyncSession]:
    """Сессия поверх соединения с открытой и всегда откатываемой транзакцией.

    Yields:
        AsyncSession: Сессия, чьи записи откатятся по выходе из теста.
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
        session = AsyncSession(bind=connection, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
    await engine.dispose()
