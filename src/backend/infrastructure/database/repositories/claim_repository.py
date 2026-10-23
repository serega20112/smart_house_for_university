"""Хранилище объявленных плат PostgreSQL."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from backend.domain.aggregates.esp_claim.esp_claim import EspClaim
from backend.domain.identifiers import (
    EspClaimId,
    UserId,
)
from backend.infrastructure.database import mappers
from backend.infrastructure.database.repositories.base import first_row
from backend.infrastructure.database.tables import (
    EspClaimRow,
)

UNIQUE_VIOLATION = "23505"
Runner = AsyncConnection | AsyncSession


class SqlClaimRepository:
    """Storage of the boards that announced themselves and wait for an owner.

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

    async def add(self, claim: EspClaim) -> None:
        """Store a new offer.

        Args:
            claim: Offer to persist.

        Returns:
            None.
        """
        values = mappers.row_values(EspClaimRow.__table__, mappers.claim_to_row(claim))
        await self._session.execute(insert(EspClaimRow.__table__).values(**values))
        await self._session.flush()

    async def current_for(self, device_key: str) -> EspClaim | None:
        """Return the newest open offer of a board.

        Args:
            device_key: Secret the board presents while connecting.

        Returns:
            EspClaim | None: Offer, or None when the board never announced itself.
        """
        result = await self._session.execute(
            select(EspClaimRow)
            .where(EspClaimRow.device_key == device_key, EspClaimRow.claimed_by.is_(None))
            .order_by(EspClaimRow.announced_at.desc(), EspClaimRow.id)
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return None if row is None else mappers.claim_from_row(row)

    async def open_with_token(self, claim_token: str) -> EspClaim | None:
        """Return the offer of a token.

        A token that was already used still resolves, so the caller can tell a
        stale offer from a made up one instead of both reading as unknown.

        Args:
            claim_token: Token shown in the interface.

        Returns:
            EspClaim | None: Offer, or None when the token is unknown.
        """
        row = await first_row(self._session, EspClaimRow, EspClaimRow.claim_token == claim_token)
        return None if row is None else mappers.claim_from_row(row)

    async def all_open(self) -> Sequence[EspClaim]:
        """Return every offer nobody took yet.

        This is a plain read: it never removes anything, not even an offer that is
        already over. Purging what expired is a separate command.

        Returns:
            Sequence[EspClaim]: Open offers.
        """
        result = await self._session.execute(
            select(EspClaimRow)
            .where(EspClaimRow.claimed_by.is_(None))
            .order_by(EspClaimRow.announced_at.desc(), EspClaimRow.id)
        )
        return [mappers.claim_from_row(row) for row in result.scalars().all()]

    async def take(self, claim_id: EspClaimId, user_id: UserId) -> bool:
        """Record conditionally that an account took the offer.

        The condition lives in the statement itself, so the store decides the
        winner of a race instead of this code deciding it from a value it read a
        moment earlier. The loser of the race sees False and changes nothing.

        Args:
            claim_id: Identifier of the offer.
            user_id: Account taking the board.

        Returns:
            bool: True when this call was the one that claimed it.
        """
        result = await self._session.execute(
            update(EspClaimRow)
            .where(EspClaimRow.id == claim_id.value, EspClaimRow.claimed_by.is_(None))
            .values(claimed_by=user_id.value)
        )
        await self._session.flush()
        return bool(result.rowcount)

    async def delete_expired(self, before: datetime) -> int:
        """Remove the offers that are over.

        This is a command and never a side effect of reading.

        Args:
            before: Moment the offers have to be older than.

        Returns:
            int: Number of removed offers.
        """
        result = await self._session.execute(
            delete(EspClaimRow).where(EspClaimRow.expires_at < before)
        )
        return int(result.rowcount or 0)
