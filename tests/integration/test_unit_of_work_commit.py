"""Явный `commit()` границы — единственный способ, которым запись уходит в PostgreSQL.

Проверка идёт к живой базе (если она поднята) и иначе пропускается, потому что именно
здесь видно то, чего не видит ни один фейк: без вызова `commit()` строка не появляется в
таблице даже для следующей транзакции, а с ним — появляется и читается заново. Это
страхует переход на явные границы сохранения (п. 4.2 ТЗ) от тихой потери записей.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from backend.config.settings import Settings
from backend.domain.aggregates.user.user import User
from backend.domain.value_objects.account.display_name import DisplayName
from backend.domain.value_objects.account.email import Email
from backend.infrastructure.database.engine import build_session_factory
from backend.infrastructure.database.unit_of_work import SqlAccountUnitOfWork

CREATED_AT = datetime(2027, 1, 1, 12, 0, tzinfo=UTC)


def _make_user() -> User:
    """Строит аккаунт с уникальным логином на этот прогон.

    Returns:
        User: Аккаунт, который не столкнётся с чужой строкой по уникальности.
    """
    return User.register(
        email=Email.parse(f"uow-{uuid4().hex}@example.com"),
        display_name=DisplayName.parse("Commit Probe"),
        password_hash="hashed-secret-value",
        created_at=CREATED_AT,
    )


@pytest_asyncio.fixture
async def account_uow_factory():
    """Даёт фабрику границ аккаунтов поверх живой базы или пропускает тест.

    Yields:
        async_sessionmaker: Фабрика сессий реальной транзакции.
    """
    engine = create_async_engine(Settings().database_url)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1 FROM users LIMIT 0"))
    except Exception as error:
        await engine.dispose()
        pytest.skip(f"PostgreSQL not reachable for commit-semantics tests: {error}")
    yield build_session_factory(engine)
    await engine.dispose()


async def test_uncommitted_write_is_not_visible(account_uow_factory) -> None:
    """Запись без `commit()` не доживает до следующей транзакции."""
    user = _make_user()

    async with SqlAccountUnitOfWork(account_uow_factory) as uow:
        await uow.accounts.add(user)

    async with SqlAccountUnitOfWork(account_uow_factory) as reader:
        assert await reader.accounts.get(user.id) is None


async def test_committed_write_is_visible(account_uow_factory) -> None:
    """Запись с `commit()` сохраняется и читается в новой транзакции, затем убирается."""
    user = _make_user()

    async with SqlAccountUnitOfWork(account_uow_factory) as uow:
        await uow.accounts.add(user)
        await uow.commit()

    try:
        async with SqlAccountUnitOfWork(account_uow_factory) as reader:
            assert await reader.accounts.get(user.id) == user
    finally:
        async with SqlAccountUnitOfWork(account_uow_factory) as cleaner:
            await cleaner.session.execute(
                text("DELETE FROM users WHERE id = :id"), {"id": user.id.value}
            )
            await cleaner.commit()
