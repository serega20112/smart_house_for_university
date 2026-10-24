"""Операции приложения, нужные транспорту платы.

Из handshake приходят три вопроса, и ни один из них не касается транспорта: какому
аккаунту принадлежит этот ключ сопряжения, видели ли плату только что и что сказать плате,
ещё не сопряжённой. Ответы держат здесь, чтобы соединение WebSocket оставалось свободным от
бизнес-логики, а транзакции жили внутри соавторов, объявленных прикладным слоем.

Объявить плату без хозяина — решение приложения, поэтому её сервис вводят переносимой
функцией, а не объектом: самому сервису нужен
:class:`~backend.application.interface.services.board_gateway.BoardGateway` — фасад над этим
же соединением, и передать их друг другу во время сборки графа нельзя. Функцию разрешают при
первом handshake, когда транспорт давно существует.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from backend.application.dto.boards.announce_board_command import AnnounceBoardCommand
from backend.application.errors import ApplicationError
from backend.application.interface.services.clock import Clock
from backend.application.interface.unit_of_work.board_onboarding import (
    BoardOnboardingUnitOfWorkFactory,
)
from backend.domain.aggregates.esp_claim.esp_claim import EspClaim
from backend.domain.exceptions import DomainError
from backend.domain.identifiers import EspDeviceId, UserId
from backend.infrastructure.logging import get_logger

log = get_logger("esp.onboarding")

AnnounceBoard = Callable[[AnnounceBoardCommand], Awaitable[EspClaim]]


@dataclass(frozen=True, slots=True)
class BoardIdentity:
    """Аккаунт, к которому относится подключившаяся плата.

    Attributes:
        user_id: Владелец платы и дома, который она питает.
        board_id: Идентификатор сопряжённой платы.
    """

    user_id: UserId
    board_id: EspDeviceId


@dataclass(frozen=True, slots=True)
class BoardAnnouncement:
    """Предложение, опубликованное для платы, у которой ещё нет хозяина.

    Attributes:
        label: Короткий код, который интерфейс показывает рядом с платой.
        ttl_sec: Сколько времени предложение остаётся годным.
    """

    label: str
    ttl_sec: int


class BoardOnboardingGateway:
    """Отвечает на вопросы handshake, идя через прикладной слой.

    Транспорт не знает ни про базы, ни про предложения: он задаёт вопросы, а этот
    шлюз превращает их в операции прикладного слоя.

    Attributes:
        onboarding_uow: Фабрика транзакций над платами.
        announce: Публикует или обновляет предложение не сопряжённой платы.
        clock: Источник текущего времени.
    """

    def __init__(
        self,
        onboarding_uow: BoardOnboardingUnitOfWorkFactory,
        announce: AnnounceBoard,
        clock: Clock,
    ) -> None:
        self._uow = onboarding_uow
        self._announce = announce
        self._clock = clock

    async def resolve_pairing_key(self, pairing_key: str) -> BoardIdentity | None:
        """Возвращает аккаунт, которому принадлежит ключ сопряжения.

        Args:
            pairing_key: Секрет, который плата предъявила в handshake.

        Returns:
            BoardIdentity | None: Владелец платы либо None, когда сервер ключа
            не знает.
        """
        async with self._uow() as uow:
            board = await uow.boards.get_by_key(pairing_key)
        if board is None:
            return None
        return BoardIdentity(user_id=board.user_id, board_id=board.id)

    async def record_last_seen(self, board_id: EspDeviceId, ssid: str | None = None) -> None:
        """Записывает, что плата только что подключилась.

        Args:
            board_id: Идентификатор платы.
            ssid: Сеть, о которой сообщила плата, либо None, если она о ней не
                сообщила.
        """
        async with self._uow() as uow:
            await uow.boards.mark_seen(board_id, self._clock.now(), ssid)

    async def announce(self, device_key: str, label: str) -> BoardAnnouncement | None:
        """Публикует предложение платы, у которой ещё нет хозяина.

        Args:
            device_key: Секрет, который плата предъявила в handshake.
            label: Короткий код, о котором сообщила плата, возможно пустой.

        Returns:
            BoardAnnouncement | None: Опубликованное предложение либо None, когда
            плату не удалось объявить.
        """
        try:
            offer = await self._announce(AnnounceBoardCommand(device_key=device_key, label=label))
        except (DomainError, ApplicationError) as error:
            log.warning("board.announcement_refused", reason=str(error))
            return None
        remaining = int((offer.expires_at - self._clock.now()).total_seconds())
        return BoardAnnouncement(label=offer.label, ttl_sec=max(remaining, 1))
