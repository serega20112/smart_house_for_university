"""Хранилище устройств на живой PostgreSQL: уникальность канала и оптимистичная блокировка.

Эти проверки идут к настоящей базе и сторожат ровно то, что не видно на моках: второй
притязанец на тот же канал отвергается ограничением уникальности, а запись по устаревшей
ревизии не перетирает свежую, а возвращается отказом. Оба правила держатся хранилищем, и
только реальный движок подтверждает, что они работают так, как рассчитывает агрегат.

"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.errors import ConcurrentModificationError
from backend.domain.aggregates.esp_device.esp_device import EspDevice
from backend.domain.aggregates.user.user import User
from backend.domain.exceptions import ChannelConflictError
from backend.domain.identifiers import UserId
from backend.domain.value_objects.account.display_name import DisplayName
from backend.domain.value_objects.account.email import Email
from backend.domain.value_objects.boards.pairing_key import PairingKey
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.relay_channel import RelayChannel
from backend.infrastructure.database.repositories.account_repository import SqlAccountRepository
from backend.infrastructure.database.repositories.board_repository import SqlBoardRepository
from backend.infrastructure.database.repositories.device_repository import SqlDeviceRepository
from tests.conftest import OWNER_UUID, make_device

CREATED_AT = datetime(2027, 1, 1, 12, 0, tzinfo=UTC)


async def _ensure_owner(session: AsyncSession) -> UserId:
    """Заводит аккаунт-владелец, на который ссылается устройство.

    Args:
        session: Сессия теста с откатываемой транзакцией.

    Returns:
        UserId: Идентификатор владельца, совпадающий с `make_device`.
    """
    owner = UserId.parse(OWNER_UUID)
    user = User(
        id=owner,
        email=Email.parse("owner@example.com"),
        password_hash="hashed",
        display_name=DisplayName.parse("Owner"),
        created_at=CREATED_AT,
    )
    await SqlAccountRepository(session).add(user)
    return owner


async def test_channel_conflict_is_rejected_by_storage(sql_session: AsyncSession) -> None:
    """Повторное притязание на занятый канал того же аккаунта отвергается базой.

    Args:
        sql_session: Сессия с откатываемой транзакцией (или пропуск без базы).

    Returns:
        None: Только проверка отказа уникальности.
    """
    owner = await _ensure_owner(sql_session)
    repository = SqlDeviceRepository(sql_session)
    first = make_device(channel=RelayChannel(11))
    await repository.add(first)

    loaded = await repository.get(owner, first.id)
    assert loaded is not None
    assert int(loaded.channel) == 11

    with pytest.raises(ChannelConflictError):
        await repository.add(make_device(name="Other lamp", channel=RelayChannel(11)))


async def test_update_on_stale_revision_raises_without_overwriting(
    sql_session: AsyncSession,
) -> None:
    """Запись по устаревшей ревизии возвращает отказ и не трогает свежую строку.

    Args:
        sql_session: Сессия с откатываемой транзакцией (или пропуск без базы).

    Returns:
        None: Только проверка оптимистичной блокировки.
    """
    owner = await _ensure_owner(sql_session)
    device = make_device(name="Heater", channel=RelayChannel(12))
    repository = SqlDeviceRepository(sql_session)
    await repository.add(device)

    fresh = await repository.get(owner, device.id)
    assert fresh is not None
    fresh.name = "Heater renamed"
    await repository.update(fresh)

    stale = await repository.get(owner, device.id)
    assert stale is not None
    stale.version = fresh.version - 1
    stale.name = "Lost writer"
    with pytest.raises(ConcurrentModificationError):
        await repository.update(stale)

    survived = await repository.get(owner, device.id)
    assert survived is not None
    assert survived.name == "Heater renamed"
    assert Capability.ON in survived.capabilities


async def test_two_boards_may_share_a_channel(sql_session: AsyncSession) -> None:
    """Один канал на двух платах живёт, а дубль канала на той же плате отвергается.

    Это и есть мультиплата: канал уникален в пределах платы, а не аккаунта, поэтому дом
    из двух плат перестаёт быть невозможным.

    Args:
        sql_session: Сессия с откатываемой транзакцией (или пропуск без базы).

    Returns:
        None: Только проверка пер-платы уникальности канала.
    """
    owner = await _ensure_owner(sql_session)
    boards = SqlBoardRepository(sql_session)
    kitchen = EspDevice.pair(owner, "Кухня", PairingKey.generate(), CREATED_AT)
    living = EspDevice.pair(owner, "Гостиная", PairingKey.generate(), CREATED_AT)
    await boards.add(kitchen)
    await boards.add(living)

    devices = SqlDeviceRepository(sql_session)
    await devices.add(make_device(name="Кухня реле", channel=RelayChannel(20), board_id=kitchen.id))
    await devices.add(
        make_device(name="Гостиная реле", channel=RelayChannel(20), board_id=living.id)
    )

    loaded = await devices.list_all(owner)
    assert {device.board_id for device in loaded} == {kitchen.id, living.id}

    with pytest.raises(ChannelConflictError):
        await devices.add(make_device(name="Дубль", channel=RelayChannel(20), board_id=kitchen.id))
