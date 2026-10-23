"""Чтения плат и открытых предложений.

Чтения стороны выбора: каждое — один вопрос и один читаемый образ.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.domain.identifiers import (
    EspClaimId,
    EspDeviceId,
    UserId,
)
from backend.domain.value_objects.boards.board_claim_view import BoardClaimView
from backend.domain.value_objects.boards.board_view import BoardView
from backend.infrastructure.database import mappers
from backend.infrastructure.database.tables import (
    EspClaimRow,
    EspDeviceRow,
)


class SqlBoardQueries:
    """Reads of the boards, answered without a transaction.

    Args:
        engine: Engine the reads are executed on.

    Returns:
        None.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        """Initialize the queries.

        Args:
            engine: Engine to read from.

        Returns:
            None.
        """
        self._engine = engine

    async def list_all(self, user_id: UserId) -> list[BoardView]:
        """Return every board of an account.

        Args:
            user_id: Owner of the boards.

        Returns:
            list[BoardView]: Boards shaped for display.
        """
        async with self._engine.connect() as connection:
            result = await connection.execute(
                select(EspDeviceRow)
                .where(EspDeviceRow.user_id == user_id.value)
                .order_by(EspDeviceRow.created_at, EspDeviceRow.id)
            )
            return [board_view_of(row) for row in result.scalars().all()]

    async def list_open_claims(self) -> list[BoardClaimView]:
        """Return every offer nobody took yet.

        Reading the list never deletes anything: an offer that is already over is
        still listed, and removing it is a separate command.

        Returns:
            list[BoardClaimView]: Open offers.
        """
        async with self._engine.connect() as connection:
            result = await connection.execute(
                select(EspClaimRow)
                .where(EspClaimRow.claimed_by.is_(None))
                .order_by(EspClaimRow.announced_at.desc(), EspClaimRow.id)
            )
            return [claim_view_of(row) for row in result.scalars().all()]


def board_view_of(row: EspDeviceRow) -> BoardView:
    """Return the read model of one stored board.

    The board is reported as offline because connectivity belongs to the live
    layer of the hardware, not to a table row.

    Args:
        row: Row to shape.

    Returns:
        BoardView: Board shaped for display.
    """
    return BoardView(
        id=EspDeviceId.parse(row.id),
        name=row.name,
        online=False,
        last_seen_at=None if row.last_seen_at is None else mappers.as_utc(row.last_seen_at),
        current_ssid=row.current_ssid,
    )


def claim_view_of(row: EspClaimRow) -> BoardClaimView:
    """Return the read model of one stored offer.

    The device key is never part of the answer: it is the credential of the board,
    and the only things a person needs are the code and the token of the offer.

    Args:
        row: Row to shape.

    Returns:
        BoardClaimView: Offer shaped for display.
    """
    return BoardClaimView(
        id=EspClaimId.parse(row.id),
        label=row.label,
        claim_token=row.claim_token,
        announced_at=mappers.as_utc(row.announced_at),
        expires_at=mappers.as_utc(row.expires_at),
    )
