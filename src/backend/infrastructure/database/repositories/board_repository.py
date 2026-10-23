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
from backend.infrastructure.database import mappers
from backend.infrastructure.database.repositories.base import first_row
from backend.infrastructure.database.tables import (
    EspDeviceRow,
)

UNIQUE_VIOLATION = "23505"
Runner = AsyncConnection | AsyncSession


class SqlBoardRepository:
    """Storage of the boards paired with accounts.

    Args:
        session: Session the unit of work opened for this transaction.

    Returns:
        None.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the repository.

        Args:
            session: Session bound to the current transaction.

        Returns:
            None.
        """
        self._session = session

    async def add(self, board: EspDevice) -> None:
        """Store a newly paired board.

        Args:
            board: Board to persist.

        Returns:
            None.
        """
        values = mappers.row_values(EspDeviceRow.__table__, mappers.board_to_row(board))
        await self._session.execute(insert(EspDeviceRow.__table__).values(**values))
        await self._session.flush()

    async def list_all(self, user_id: UserId) -> Sequence[EspDevice]:
        """Return every board of an account.

        Args:
            user_id: Owner of the boards.

        Returns:
            Sequence[EspDevice]: Boards of the account.
        """
        result = await self._session.execute(
            select(EspDeviceRow)
            .where(EspDeviceRow.user_id == user_id.value)
            .order_by(EspDeviceRow.created_at, EspDeviceRow.id)
        )
        return [mappers.board_from_row(row) for row in result.scalars().all()]

    async def get(self, user_id: UserId, board_id: EspDeviceId) -> EspDevice | None:
        """Return one board of an account.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.

        Returns:
            EspDevice | None: Board, or None when the account has no such one.
        """
        row = await first_row(
            self._session,
            EspDeviceRow,
            EspDeviceRow.id == board_id.value,
            EspDeviceRow.user_id == user_id.value,
        )
        return None if row is None else mappers.board_from_row(row)

    async def get_by_key(self, pairing_key: str) -> EspDevice | None:
        """Return the board presenting a pairing key.

        This is the lookup the board handshake resolves before anything else: the
        key the board presents is what turns a connection into a home.

        Args:
            pairing_key: Secret presented during the handshake.

        Returns:
            EspDevice | None: Board, or None when the key is unknown.
        """
        row = await first_row(self._session, EspDeviceRow, EspDeviceRow.pairing_key == pairing_key)
        return None if row is None else mappers.board_from_row(row)

    async def mark_seen(
        self, board_id: EspDeviceId, seen_at: datetime, ssid: str | None = None
    ) -> None:
        """Record that a board has just connected.

        Only the timestamp and the network are written. The board is not read
        first and is not written back whole, so two handshakes of the same board
        cannot overwrite each other's configuration.

        Args:
            board_id: Identifier of the board.
            seen_at: Moment of the successful handshake.
            ssid: Network the board reported being on, or None when it did not
                report one and the previous answer stays.

        Returns:
            None.
        """
        values: dict[str, object] = {"last_seen_at": seen_at}
        if ssid is not None:
            values["current_ssid"] = ssid
        await self._session.execute(
            update(EspDeviceRow).where(EspDeviceRow.id == board_id.value).values(**values)
        )
        await self._session.flush()

    async def delete(self, user_id: UserId, board_id: EspDeviceId) -> bool:
        """Remove a board of an account.

        Args:
            user_id: Owner of the board.
            board_id: Identifier of the board.

        Returns:
            bool: True when a board was removed.
        """
        result = await self._session.execute(
            delete(EspDeviceRow).where(
                EspDeviceRow.id == board_id.value, EspDeviceRow.user_id == user_id.value
            )
        )
        return bool(result.rowcount)
