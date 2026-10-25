"""Чтения плат и открытых предложений.

Чтения стороны выбора: каждое — один вопрос и один читаемый образ.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.application.dto.views.board_claim_view import BoardClaimView
from backend.application.dto.views.board_view import BoardView
from backend.domain.identifiers import (
    EspClaimId,
    EspDeviceId,
    UserId,
)
from backend.infrastructure.database.mappers.base import as_utc
from backend.infrastructure.database.models import (
    EspClaimModel,
    EspDeviceModel,
)


class SqlBoardQueries:
    """Чтения плат без явной транзакции.

    Чтения идут через сессию, а не через голое соединение: только сессия гидратирует
    ORM-сущности, и потому `select(EspDeviceModel)` отдаёт строку-плату, а не первый
    столбец.

    Attributes:
        session_factory: Фабрика сессий, на которой выполняют чтения.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Инициализирует чтения.

        Args:
            session_factory: Фабрика сессий, из которой читают.
        """
        self._session_factory = session_factory

    async def list_all(self, user_id: UserId) -> list[BoardView]:
        """Возвращает все платы аккаунта.

        Args:
            user_id: Владелец плат.

        Returns:
            list[BoardView]: Платы, приготовленные для показа.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(EspDeviceModel)
                .where(EspDeviceModel.user_id == user_id.value)
                .order_by(EspDeviceModel.created_at, EspDeviceModel.id)
            )
            return [board_view_of(row) for row in result.scalars().all()]

    async def list_open_claims(self, now: datetime) -> list[BoardClaimView]:
        """Возвращает предложения, которые ещё не взяты и ещё действительны.

        Просроченное объявление в список не попадает: с этого момента плату нельзя
        забрать, и показывать её человеку незачем. Саму строку убирает отдельная
        команда чистки — чтение базу не меняет.

        Args:
            now: Момент, относительно которого проверяют срок предложения.

        Returns:
            list[BoardClaimView]: Открытые предложения.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(EspClaimModel)
                .where(
                    EspClaimModel.claimed_by.is_(None),
                    EspClaimModel.expires_at > now,
                )
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
