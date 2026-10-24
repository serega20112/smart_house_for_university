"""Хранилище логических устройств PostgreSQL."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import delete, insert, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from backend.application.errors import (
    ConcurrentModificationError,
)
from backend.domain.aggregates.device.device import Device
from backend.domain.exceptions import ChannelConflictError
from backend.domain.identifiers import (
    DeviceId,
    UserId,
)
from backend.infrastructure.database import mappers
from backend.infrastructure.database.repositories.base import (
    every_row,
    first_row,
    insert_rows,
    is_unique_violation,
)
from backend.infrastructure.database.repositories.child_rows import capabilities_of
from backend.infrastructure.database.tables import (
    DeviceCapabilityRow,
    DeviceRow,
)

UNIQUE_VIOLATION = "23505"
Runner = AsyncConnection | AsyncSession


class SqlDeviceRepository:
    """Хранение логических устройств одного аккаунта.

    Attributes:
        session: Сессия, которую открыла для этой транзакции граница.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует хранилище.

        Args:
            session: Сессия, привязанная к нынешней транзакции.
        """
        self._session = session

    async def list_all(self, user_id: UserId) -> Sequence[Device]:
        """Возвращает все устройства аккаунта.

        Args:
            user_id: Владелец устройств.

        Returns:
            Sequence[Device]: Настроенные устройства.
        """
        rows = await every_row(self._session, DeviceRow, DeviceRow.user_id == user_id.value)
        stored = await capabilities_of(self._session, [row.id for row in rows])
        return [mappers.device_from_row(row, stored.get(row.id, frozenset())) for row in rows]

    async def get(self, user_id: UserId, device_id: DeviceId) -> Device | None:
        """Возвращает одно устройство аккаунта.

        Поиск ограничен владельцем, поэтому устройство чужого аккаунта читается как
        отсутствующее, а не раздаётся дальше.

        Args:
            user_id: Владелец устройства.
            device_id: Идентификатор устройства.

        Returns:
            Device | None: Устройство или None, когда у аккаунта такого нет.
        """
        row = await first_row(
            self._session,
            DeviceRow,
            DeviceRow.id == device_id.value,
            DeviceRow.user_id == user_id.value,
        )
        if row is None:
            return None
        stored = await capabilities_of(self._session, [row.id])
        return mappers.device_from_row(row, stored.get(row.id, frozenset()))

    async def add(self, device: Device) -> None:
        """Сохраняет только что созданное устройство.

        Строку устройства пишут раньше его способностей, потому что каждая строка
        способности несёт на неё внешний ключ. Канал, к которому подключают устройство,
        у каждого аккаунта один, поэтому второе притязание отвергает хранилище, а не
        поиск, решивший это мгновением раньше.

        Args:
            device: Устройство для записи.

        Raises:
            ChannelConflictError: Когда канал уже подключён к другому устройству того
                же аккаунта.
        """
        values = mappers.row_values(DeviceRow.__table__, mappers.device_to_row(device))
        try:
            await self._session.execute(insert(DeviceRow.__table__).values(**values))
            await insert_rows(
                self._session, DeviceCapabilityRow.__table__, mappers.capability_rows(device)
            )
            await self._session.flush()
        except IntegrityError as error:
            if not is_unique_violation(error):
                raise
            raise ChannelConflictError(int(device.channel)) from error

    async def update(self, device: Device) -> None:
        """Сохраняет изменённое устройство по ревизии, которую оно действительно видело.

        Запрос несёт ревизию, на которой агрегат прочитали: хранилище не меняет ничего,
        если строку тем временем задели. Способности заменяют целиком, а не сливают:
        агрегат держит множество полностью, и способность, которой в нём больше нет,
        убрали нарочно.

        Args:
            device: Устройство для записи.

        Raises:
            ConcurrentModificationError: Когда строка ушла вперёд с момента чтения.
            ChannelConflictError: Когда новый канал уже подключён к другому устройству
                того же аккаунта.
        """
        row = mappers.device_to_row(device)
        try:
            result = await self._session.execute(
                update(DeviceRow)
                .where(
                    DeviceRow.id == device.id.value,
                    DeviceRow.user_id == device.user_id.value,
                    DeviceRow.version == device.version,
                )
                .values(
                    name=row.name,
                    kind=row.kind,
                    channel=row.channel,
                    enabled=row.enabled,
                    automation_enabled=row.automation_enabled,
                    version=device.version + 1,
                )
            )
            await self._session.flush()
        except IntegrityError as error:
            if not is_unique_violation(error):
                raise
            raise ChannelConflictError(int(device.channel)) from error
        if not result.rowcount:
            raise ConcurrentModificationError("device", device.id)
        device.version += 1
        await self._session.execute(
            delete(DeviceCapabilityRow).where(DeviceCapabilityRow.device_id == device.id.value)
        )
        await insert_rows(
            self._session, DeviceCapabilityRow.__table__, mappers.capability_rows(device)
        )
        await self._session.flush()

    async def delete(self, user_id: UserId, device_id: DeviceId) -> bool:
        """Убирает устройство аккаунта.

        Способности, участие в автоматизации и карточки панели, смотревшие на это
        устройство, снимают каскадные внешние ключи хранилища, поэтому ни одна строка
        не выживает, описывая то, чего больше нет.

        Args:
            user_id: Владелец устройства.
            device_id: Идентификатор устройства.

        Returns:
            bool: True, когда устройство убрали.
        """
        result = await self._session.execute(
            delete(DeviceRow).where(
                DeviceRow.id == device_id.value, DeviceRow.user_id == user_id.value
            )
        )
        return bool(result.rowcount)
