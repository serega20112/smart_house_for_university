"""Хранилище объявленных плат на живой PostgreSQL: забрать может ровно один.

Гонку за плату решает хранилище условной записью, а не чтением на мгновение раньше,
поэтому проверка идёт к настоящей базе: первое взятие возвращает `True` и закрепляет
владельца, второе — `False`, потому что строка уже заявлена, а поиск открытого предложения
больше ничего не находит.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.aggregates.user.user import User
from backend.domain.entities.esp_claim.esp_claim import EspClaim
from backend.domain.identifiers import UserId
from backend.domain.value_objects.account.display_name import DisplayName
from backend.domain.value_objects.account.email import Email
from backend.domain.value_objects.boards.pairing_key import PairingKey
from backend.infrastructure.database.repositories.account_repository import SqlAccountRepository
from backend.infrastructure.database.repositories.claim_repository import SqlClaimRepository
from tests.conftest import OWNER_UUID

NOW = datetime(2027, 5, 1, 12, 0, tzinfo=UTC)


async def _ensure_owner(session: AsyncSession) -> UserId:
    """Заводит аккаунт, который заберёт плату.

    Args:
        session: Сессия теста с откатываемой транзакцией.

    Returns:
        UserId: Идентификатор владельца.
    """
    owner = UserId.parse(OWNER_UUID)
    user = User(
        id=owner,
        email=Email.parse("claim-owner@example.com"),
        password_hash="hashed",
        display_name=DisplayName.parse("Claim Owner"),
        created_at=NOW,
    )
    await SqlAccountRepository(session).add(user)
    return owner


async def test_only_first_account_can_take_a_claim(sql_session: AsyncSession) -> None:
    """Первый взятие закрепляет плату, второе не получает ничего.

    Args:
        sql_session: Сессия с откатываемой транзакцией (или пропуск без базы).

    Returns:
        None: Только проверка условного забирания и очистки истёкших.
    """
    owner = await _ensure_owner(sql_session)
    challenger = UserId.generate()
    repository = SqlClaimRepository(sql_session)
    claim = EspClaim.announce(
        device_key=PairingKey.generate(), label="ABCD", announced_at=NOW, ttl_sec=120
    )
    await repository.add(claim)

    found = await repository.current_for(claim.device_key.value)
    assert found is not None
    assert found.id == claim.id

    assert await repository.take(claim.id, owner) is True
    assert await repository.take(claim.id, challenger) is False
    assert await repository.current_for(claim.device_key.value) is None

    assert await repository.delete_expired(NOW + timedelta(days=1)) >= 1
