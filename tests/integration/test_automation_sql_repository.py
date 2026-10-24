"""Хранилище настройки автоматизации на живой PostgreSQL: чтение пустого и цикл записи.

Проверка идёт к настоящей базе и подтверждает, что отсутствующая настройка читается как
`None` (без молчаливой вставки строки по умолчанию), а после записи её можно прочитать
обратно с теми же значениями — то есть маппер, upsert и запрос согласованы со схемой.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.aggregates.automation.automation_settings import AutomationSettings
from backend.domain.aggregates.user.user import User
from backend.domain.identifiers import UserId
from backend.domain.value_objects.account.display_name import DisplayName
from backend.domain.value_objects.account.email import Email
from backend.infrastructure.database.repositories.account_repository import SqlAccountRepository
from backend.infrastructure.database.repositories.automation_repository import (
    SqlAutomationRepository,
)
from tests.conftest import OWNER_UUID

CREATED_AT = datetime(2027, 1, 1, 12, 0, tzinfo=UTC)


async def _ensure_owner(session: AsyncSession) -> UserId:
    """Заводит аккаунт, на который ссылается строка автоматизации.

    Args:
        session: Сессия теста с откатываемой транзакцией.

    Returns:
        UserId: Идентификатор владельца.
    """
    owner = UserId.parse(OWNER_UUID)
    user = User(
        id=owner,
        email=Email.parse("auto-owner@example.com"),
        password_hash="hashed",
        display_name=DisplayName.parse("Auto Owner"),
        created_at=CREATED_AT,
    )
    await SqlAccountRepository(session).add(user)
    return owner


async def test_absent_then_saved_automation_round_trips_on_real_postgres(
    sql_session: AsyncSession,
) -> None:
    """Отсутствующая настройка читается как None, записанная — возвращается целиком.

    Args:
        sql_session: Сессия с откатываемой транзакцией (или пропуск без базы).

    Returns:
        None: Только проверка чтения пустого и цикла записи.
    """
    owner = await _ensure_owner(sql_session)
    repository = SqlAutomationRepository(sql_session)

    assert await repository.get(owner) is None

    settings = AutomationSettings.create(owner)
    await repository.save(settings)

    loaded = await repository.get(owner)
    assert loaded is not None
    assert loaded.user_id == owner
    assert loaded.target_temperature == settings.target_temperature
    assert loaded.target_humidity == settings.target_humidity
