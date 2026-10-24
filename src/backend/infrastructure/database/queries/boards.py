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
from backend.infrastructure.database.mappers.base import as_utc
from backend.infrastructure.database.models import (
    EspClaimModel,
    EspDeviceModel,
)


class SqlBoardQueries:
    """Чтения плат без транзакции.

    Attributes:
        engine: Движок, на котором выполняют чтения.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        """Инициализирует чтения.

        Args:
            engine: Движок, из которого читают.
        """
        self._engine = engine

    async def list_all(self, user_id: UserId) -> list[BoardView]:
        """Возвращает все платы аккаунта.

        Args:
            user_id: Владелец плат.

        Returns:
            list[BoardView]: Платы, приготовленные для показа.
        """
        async with self._engine.connect() as connection:
            result = await connection.execute(
                select(EspDeviceModel)
                .where(EspDeviceModel.user_id == user_id.value)
                .order_by(EspDeviceModel.created_at, EspDeviceModel.id)
            )
            return [board_view_of(row) for row in result.scalars().all()]

    async def list_open_claims(self) -> list[BoardClaimView]:
        """Возвращает всякое предложение, которое ещё никто не забрал.

        Чтение списка ничего не удаляет: уже просроченное предложение всё равно
        показывается, а убирает его отдельная команда.

        Returns:
            list[BoardClaimView]: Открытые предложения.
        """
        async with self._engine.connect() as connection:
            result = await connection.execute(
                select(EspClaimModel)
                .where(EspClaimModel.claimed_by.is_(None))
                .order_by(EspClaimModel.announced_at.desc(), EspClaimModel.id)
            )
            return [claim_view_of(row) for row in result.scalars().all()]


def board_view_of(row: EspDeviceModel) -> BoardView:
    """Возвращает модель чтения одной сохранённой платы.

    Плата всегда показывается отключённой: доступность относится к живому слою железа,
    а не к строке таблицы.

    Args:
        row: Строка, которую превращают в образ.

    Returns:
        BoardView: Плата, приготовленная для показа.
    """
    return BoardView(
        id=EspDeviceId.parse(row.id),
        name=row.name,
        online=False,
        last_seen_at=None if row.last_seen_at is None else as_utc(row.last_seen_at),
        current_ssid=row.current_ssid,
    )


def claim_view_of(row: EspClaimModel) -> BoardClaimView:
    """Возвращает модель чтения одного сохранённого предложения.

    Ключ устройства в ответ не входит никогда: это учётные данные платы, а человеку
    нужны только код и токен предложения.

    Args:
        row: Строка, которую превращают в образ.

    Returns:
        BoardClaimView: Предложение, приготовленное для показа.
    """
    return BoardClaimView(
        id=EspClaimId.parse(row.id),
        label=row.label,
        claim_token=row.claim_token,
        announced_at=as_utc(row.announced_at),
        expires_at=as_utc(row.expires_at),
    )
