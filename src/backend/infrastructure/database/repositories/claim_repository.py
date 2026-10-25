"""Хранилище объявленных плат PostgreSQL."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from backend.application.interfaces.repositories.board_repository import ClaimRepository
from backend.domain.entities.esp_claim.esp_claim import EspClaim
from backend.domain.identifiers import (
    EspClaimId,
    UserId,
)
from backend.infrastructure.database.mappers.boards import claim_from_row, claim_to_row
from backend.infrastructure.database.models import (
    EspClaimModel,
)
from backend.infrastructure.database.repositories.base import (
    affected_rows,
    first_row,
    row_values,
)

UNIQUE_VIOLATION = "23505"
Runner = AsyncConnection | AsyncSession


class SqlClaimRepository(ClaimRepository):
    """Хранение плат, которые объявились и ждут хозяина.

    Attributes:
        session: Сессия, которую открыла для этой транзакции граница.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует хранилище.

        Args:
            session: Сессия, привязанная к нынешней транзакции.
        """
        self._session = session

    async def add(self, claim: EspClaim) -> None:
        """Сохраняет новое предложение.

        Args:
            claim: Предложение для записи.
        """
        values = row_values(EspClaimModel.__table__, claim_to_row(claim))
        await self._session.execute(insert(EspClaimModel.__table__).values(**values))
        await self._session.flush()

    async def current_for(self, device_key: str) -> EspClaim | None:
        """Возвращает самое свежее открытое предложение платы.

        Args:
            device_key: Секрет, который плата предъявляет при соединении.

        Returns:
            EspClaim | None: Предложение или None, когда плата о себе не объявляла.
        """
        result = await self._session.execute(
            select(EspClaimModel)
            .where(EspClaimModel.device_key == device_key, EspClaimModel.claimed_by.is_(None))
            .order_by(EspClaimModel.announced_at.desc(), EspClaimModel.id)
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return None if row is None else claim_from_row(row)

    async def open_with_token(self, claim_token: str) -> EspClaim | None:
        """Возвращает предложение по его токену.

        Использованный токен тоже разрешается, чтобы вызывающий различил устаревшее
        предложение от выдуманного, а не получил «неизвестно» на оба.

        Args:
            claim_token: Токен, показанный в интерфейсе.

        Returns:
            EspClaim | None: Предложение или None, когда токен неизвестен.
        """
        row = await first_row(
            self._session, EspClaimModel, EspClaimModel.claim_token == claim_token
        )
        return None if row is None else claim_from_row(row)

    async def take(self, claim_id: EspClaimId, user_id: UserId) -> bool:
        """Выборочно записывает, что аккаунт забрал предложение.

        Условие живёт в самом запросе, поэтому победителя гонки решает хранилище, а не
        этот код по значению, прочитанному мгновением раньше. Проигравший видит False и
        не меняет ничего.

        Args:
            claim_id: Идентификатор предложения.
            user_id: Аккаунт, который забирает плату.

        Returns:
            bool: True, когда именно этот вызов забрал предложение.
        """
        result = await self._session.execute(
            update(EspClaimModel)
            .where(EspClaimModel.id == claim_id.value, EspClaimModel.claimed_by.is_(None))
            .values(claimed_by=user_id.value)
        )
        await self._session.flush()
        return affected_rows(result) > 0

    async def delete_expired(self, before: datetime) -> int:
        """Убирает предложения, которые перестали быть действительными.

        Это команда, а не побочный эффект чтения.

        Args:
            before: Момент, старее которого должны быть предложения.

        Returns:
            int: Число убранных предложений.
        """
        result = await self._session.execute(
            delete(EspClaimModel).where(EspClaimModel.expires_at < before)
        )
        return affected_rows(result)
