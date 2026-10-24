"""Хранилище сценариев на живой PostgreSQL: запись, чтение и оптимистичная блокировка.

Сценарий доходит до финальной стадии и остаётся в истории, поэтому проверки идут к
настоящей базе и подтверждают, что добавленный сценарий читается, держится в приоритетных
, пока ожидает, и что запись по чужой ревизии отвергается хранилищем, а не перетирается.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.errors import ConcurrentModificationError
from backend.domain.aggregates.scenario.scenario import Scenario
from backend.domain.aggregates.user.user import User
from backend.domain.identifiers import ScenarioId, UserId
from backend.domain.value_objects.account.display_name import DisplayName
from backend.domain.value_objects.account.email import Email
from backend.domain.value_objects.scenario.scenario_status import ScenarioStatus
from backend.infrastructure.database.repositories.account_repository import SqlAccountRepository
from backend.infrastructure.database.repositories.scenario_repository import SqlScenarioRepository
from tests.conftest import OWNER_UUID

NOW = datetime(2027, 5, 1, 12, 0, tzinfo=UTC)


async def _ensure_owner(session: AsyncSession) -> UserId:
    """Заводит аккаунт-владелец сценариев.

    Args:
        session: Сессия теста с откатываемой транзакцией.

    Returns:
        UserId: Идентификатор владельца.
    """
    owner = UserId.parse(OWNER_UUID)
    user = User(
        id=owner,
        email=Email.parse("scenario-owner@example.com"),
        password_hash="hashed",
        display_name=DisplayName.parse("Scenario Owner"),
        created_at=NOW,
    )
    await SqlAccountRepository(session).add(user)
    return owner


def _pending(owner: UserId) -> Scenario:
    """Строит ожидающий сценарий на минуту позже текущего момента.

    Args:
        owner: Владелец сценария.

    Returns:
        Scenario: Сценарий в стадии ожидания.
    """
    return Scenario(
        id=ScenarioId.generate(),
        user_id=owner,
        status=ScenarioStatus.PENDING,
        created_at=NOW,
        start_at=NOW + timedelta(minutes=1),
    )


async def test_scenario_add_get_and_holding_priority_on_real_postgres(
    sql_session: AsyncSession,
) -> None:
    """Добавленный сценарий читается и числится приоритетным автоматике.

    Args:
        sql_session: Сессия с откатываемой транзакцией (или пропуск без базы).

    Returns:
        None: Только проверка записи, чтения и приоритетного списка.
    """
    owner = await _ensure_owner(sql_session)
    repository = SqlScenarioRepository(sql_session)
    scenario = _pending(owner)

    await repository.add(scenario)

    loaded = await repository.get(owner, scenario.id)
    assert loaded is not None
    assert loaded.status is ScenarioStatus.PENDING

    holding = await repository.list_holding_priority(owner)
    assert any(item.id == scenario.id for item in holding)


async def test_scenario_update_on_stale_revision_raises(sql_session: AsyncSession) -> None:
    """Запись сценария по несуществующей ревизии возвращает отказ.

    Args:
        sql_session: Сессия с откатываемой транзакцией (или пропуск без базы).

    Returns:
        None: Только проверка отказа оптимистичной блокировки.
    """
    owner = await _ensure_owner(sql_session)
    repository = SqlScenarioRepository(sql_session)
    scenario = _pending(owner)
    await repository.add(scenario)

    stale = await repository.get(owner, scenario.id)
    assert stale is not None
    stale.version = 999
    with pytest.raises(ConcurrentModificationError):
        await repository.update(stale)
