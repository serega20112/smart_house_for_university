"""Хранилище сетей плат PostgreSQL."""

from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from backend.domain.aggregates.board_network.board_network import BoardNetwork
from backend.domain.identifiers import (
    EspDeviceId,
)
from backend.infrastructure.database import mappers
from backend.infrastructure.database.repositories.base import (
    first_row,
    upsert_columns,
)
from backend.infrastructure.database.tables import (
    BoardNetworkRow,
)

UNIQUE_VIOLATION = "23505"
Runner = AsyncConnection | AsyncSession


class SqlBoardNetworkRepository:
    """Storage of the network each board is told to use.

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

    async def get(self, board_id: EspDeviceId) -> BoardNetwork | None:
        """Return the network of one board.

        Args:
            board_id: Identifier of the board.

        Returns:
            BoardNetwork | None: Network of that board, or None when it was
            never configured.
        """
        row = await first_row(
            self._session, BoardNetworkRow, BoardNetworkRow.board_id == board_id.value
        )
        return None if row is None else mappers.network_from_row(row)

    async def save(self, network: BoardNetwork) -> None:
        """Store the network of a board.

        The row is written whole, so a change of any of the values replaces the
        previous ones instead of leaving a part of the old network behind.

        Args:
            network: Network to persist.

        Returns:
            None.
        """
        values = mappers.row_values(BoardNetworkRow.__table__, mappers.network_to_row(network))
        await self._session.execute(
            postgresql.insert(BoardNetworkRow.__table__)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[BoardNetworkRow.__table__.c.board_id],
                set_=upsert_columns(BoardNetworkRow.__table__, "board_id", "user_id"),
            )
        )
        await self._session.flush()

    async def delete(self, board_id: EspDeviceId) -> bool:
        """Remove the network of a board.

        Args:
            board_id: Identifier of the board.

        Returns:
            bool: True when a network was removed.
        """
        result = await self._session.execute(
            delete(BoardNetworkRow).where(BoardNetworkRow.board_id == board_id.value)
        )
        return bool(result.rowcount)
