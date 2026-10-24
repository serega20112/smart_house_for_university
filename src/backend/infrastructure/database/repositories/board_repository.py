"""Хранилище сопряжённых плат PostgreSQL."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from backend.domain.aggregates.esp_device.esp_device import EspDevice
from backend.domain.identifiers import (
    EspDeviceId,
    UserId,
)
from backend.infrastructure.database.mappers.boards import board_from_row, board_to_row
from backend.infrastructure.database.models import (
    EspDeviceModel,
)
from backend.infrastructure.database.repositories.base import first_row, row_values

UNIQUE_VIOLATION = "23505"
Runner = AsyncConnection | AsyncSession


class SqlBoardRepository:
    """Хранение плат, сопряжённых с аккаунтами.

    Attributes:
        session: Сессия, которую открыла для этой транзакции граница.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует хранилище.

        Args:
            session: Сессия, привязанная к нынешней транзакции.
        """
        self._session = session

    async def add(self, board: EspDevice) -> None:
        """Сохраняет только что сопряжённую плату.

        Args:
            board: Плата для записи.
        """
        values = row_values(EspDeviceModel.__table__, board_to_row(board))
        await self._session.execute(insert(EspDeviceModel.__table__).values(**values))
        await self._session.flush()

    async def list_all(self, user_id: UserId) -> Sequence[EspDevice]:
        """Возвращает все платы аккаунта.

        Args:
            user_id: Владелец плат.

        Returns:
            Sequence[EspDevice]: Платы аккаунта.
        """
        result = await self._session.execute(
            select(EspDeviceModel)
            .where(EspDeviceModel.user_id == user_id.value)
            .order_by(EspDeviceModel.created_at, EspDeviceModel.id)
        )
        return [board_from_row(row) for row in result.scalars().all()]

    async def get(self, user_id: UserId, board_id: EspDeviceId) -> EspDevice | None:
        """Возвращает одну плату аккаунта.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.

        Returns:
            EspDevice | None: Плата или None, когда у аккаунта такой нет.
        """
        row = await first_row(
            self._session,
            EspDeviceModel,
            EspDeviceModel.id == board_id.value,
            EspDeviceModel.user_id == user_id.value,
        )
        return None if row is None else board_from_row(row)

    async def get_by_key(self, pairing_key: str) -> EspDevice | None:
        """Возвращает плату, предъявившую ключ сопряжения.

        Это тот поиск, которым handshake платы разрешается прежде всего: именно ключ,
        который плата предъявляет, превращает соединение в чей-то дом.

        Args:
            pairing_key: Секрет, предъявленный при handshake.

        Returns:
            EspDevice | None: Плата или None, когда ключ неизвестен.
        """
        row = await first_row(
            self._session, EspDeviceModel, EspDeviceModel.pairing_key == pairing_key
        )
        return None if row is None else board_from_row(row)

    async def mark_seen(
        self, board_id: EspDeviceId, seen_at: datetime, ssid: str | None = None
    ) -> None:
        """Записывает, что плата подключилась только что.

        Пишут только отметку времени и сеть. Плату не читают заранее и не возвращают
        целиком, поэтому два handshake одной платы не могут перетереть настройку друг
        друга.

        Args:
            board_id: Идентификатор платы.
            seen_at: Момент успешного handshake.
            ssid: Сеть, о которой сообщила плата, или None, когда она ничего не
                сообщила и прежний ответ остаётся.
        """
        values: dict[str, object] = {"last_seen_at": seen_at}
        if ssid is not None:
            values["current_ssid"] = ssid
        await self._session.execute(
            update(EspDeviceModel).where(EspDeviceModel.id == board_id.value).values(**values)
        )
        await self._session.flush()

    async def delete(self, user_id: UserId, board_id: EspDeviceId) -> bool:
        """Убирает плату аккаунта.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.

        Returns:
            bool: True, когда плату убрали.
        """
        result = await self._session.execute(
            delete(EspDeviceModel).where(
                EspDeviceModel.id == board_id.value, EspDeviceModel.user_id == user_id.value
            )
        )
        return bool(result.rowcount)
