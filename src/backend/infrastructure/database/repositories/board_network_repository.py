"""Хранилище сетей плат PostgreSQL."""

from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from backend.application.interfaces.repositories.board_repository import BoardNetworkRepository
from backend.domain.entities.boards.board_network import BoardNetwork
from backend.domain.identifiers import (
    EspDeviceId,
)
from backend.infrastructure.database.mappers.boards import network_from_row, network_to_row
from backend.infrastructure.database.models import (
    BoardNetworkModel,
)
from backend.infrastructure.database.repositories.base import (
    affected_rows,
    first_row,
    row_values,
    upsert_columns,
)

UNIQUE_VIOLATION = "23505"
Runner = AsyncConnection | AsyncSession


class SqlBoardNetworkRepository(BoardNetworkRepository):
    """Хранение сети, которую предписано использовать каждой плате.

    Attributes:
        session: Сессия, которую открыла для этой транзакции граница.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует хранилище.

        Args:
            session: Сессия, привязанная к нынешней транзакции.
        """
        self._session = session

    async def get(self, board_id: EspDeviceId) -> BoardNetwork | None:
        """Возвращает сеть одной платы.

        Args:
            board_id: Идентификатор платы.

        Returns:
            BoardNetwork | None: Сеть этой платы или None, когда её ни разу не
                настраивали.
        """
        row = await first_row(
            self._session, BoardNetworkModel, BoardNetworkModel.board_id == board_id.value
        )
        return None if row is None else network_from_row(row)

    async def save(self, network: BoardNetwork) -> None:
        """Сохраняет сеть платы.

        Строку пишут целиком, поэтому изменение любого значения заменяет прежние, а не
        оставляет часть старой сети лежать рядом с новой.

        Args:
            network: Сеть для записи.
        """
        values = row_values(BoardNetworkModel.__table__, network_to_row(network))
        await self._session.execute(
            postgresql.insert(BoardNetworkModel.__table__)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[BoardNetworkModel.__table__.c.board_id],
                set_=upsert_columns(BoardNetworkModel.__table__, "board_id", "user_id"),
            )
        )
        await self._session.flush()

    async def delete(self, board_id: EspDeviceId) -> bool:
        """Убирает сеть платы.

        Args:
            board_id: Идентификатор платы.

        Returns:
            bool: True, когда сеть убрали.
        """
        result = await self._session.execute(
            delete(BoardNetworkModel).where(BoardNetworkModel.board_id == board_id.value)
        )
        return affected_rows(result) > 0
