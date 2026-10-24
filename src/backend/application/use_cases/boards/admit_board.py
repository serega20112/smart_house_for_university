"""Допуск платы, которая дозвонилась: владелец, объявление или отказ.

Решение принимает прикладной слой, а не транспорт: неизвестный ключ — это плата без
хозяина, даже если её собственная флешка утверждает обратное, и объявлять плату нужно
через тот же сервис, который публикует её в интерфейс.
"""

from __future__ import annotations

from backend.application.dto.boards.announce_board_command import AnnounceBoardCommand
from backend.application.dto.boards.board_admission import (
    BoardAdmission,
    BoardGreeting,
    BoardOffer,
    BoardOwner,
    BoardRefusal,
)
from backend.application.errors import ApplicationError
from backend.application.interfaces.services.boards.board_announcer import BoardAnnouncer
from backend.application.interfaces.services.system.clock import Clock
from backend.application.interfaces.unit_of_work.board_onboarding import (
    BoardOnboardingUnitOfWorkFactory,
)
from backend.domain.exceptions import DomainError
from backend.domain.policies.board_admission import AdmissionKind, BoardAdmissionPolicy

MISSING_KEY_REASON = "missing_pairing_key"
UNKNOWN_KEY_REASON = "unknown_pairing_key"


class AdmitBoardUseCase:
    """Отвечает на handshake платы.

    Args:
        onboarding_uow: Фабрика транзакций над платами.
        announcer: Публикует плату, у которой ещё нет хозяина.
        clock: Источник текущего времени.
    """

    def __init__(
        self,
        onboarding_uow: BoardOnboardingUnitOfWorkFactory,
        announcer: BoardAnnouncer,
        clock: Clock,
    ) -> None:
        """Инициализирует допуск платы."""
        self._uow = onboarding_uow
        self._announcer = announcer
        self._clock = clock
        self._policy = BoardAdmissionPolicy()

    async def execute(self, greeting: BoardGreeting) -> BoardAdmission:
        """Разрешает предъявленный ключ и возвращает ответ плате.

        Плата, чей ключ найден, отмечает своё присутствие вместе с сетью, о которой
        она сообщила, и получает хозяина. Остальные ответы транспорт доносит сам:
        предложение забрать плату либо отказ с закрытием соединения.

        Args:
            greeting: Первое сообщение платы.

        Returns:
            BoardAdmission: Владелец, предложение хозяину или отказ.
        """
        admitted = await self._find(greeting)
        kind = self._policy.decide(
            key_presented=bool(greeting.pairing_key),
            known_board=admitted is not None,
            board_claims_owned=greeting.claims_owned,
        )
        if kind is AdmissionKind.REFUSED:
            return BoardRefusal(
                reason=(MISSING_KEY_REASON if not greeting.pairing_key else UNKNOWN_KEY_REASON)
            )
        if kind is AdmissionKind.GRANTED and admitted is not None:
            return admitted
        offer = await self._announce(greeting)
        return offer or BoardRefusal(reason=UNKNOWN_KEY_REASON)

    async def _find(self, greeting: BoardGreeting) -> BoardOwner | None:
        """Находит плату по ключу и записывает, что она только что подключилась.

        Args:
            greeting: Первое сообщение платы.

        Returns:
            BoardOwner | None: Владелец платы либо None, когда сервер ключа не знает.
        """
        if not greeting.pairing_key:
            return None
        now = self._clock.now()
        async with self._uow() as uow:
            board = await uow.boards.get_by_key(greeting.pairing_key)
            if board is None:
                return None
            await uow.boards.mark_seen(board.id, now, greeting.ssid)
            return BoardOwner(user_id=board.user_id, board_id=board.id)

    async def _announce(self, greeting: BoardGreeting) -> BoardOffer | None:
        """Объявляет плату, ключ которой сервер не знает.

        Отказ хранилища остаётся отказом в соединении, а не аварией: плата
        перепозвонится сама, когда её заберут из интерфейса.

        Args:
            greeting: Первое сообщение платы.

        Returns:
            BoardOffer | None: Открытое предложение либо None, когда плату объявить
            не удалось.
        """
        try:
            claim = await self._announcer.announce(
                AnnounceBoardCommand(device_key=greeting.pairing_key or "", label=greeting.label)
            )
        except (DomainError, ApplicationError):
            return None
        return BoardOffer(
            label=claim.label,
            ttl_sec=self._policy.offer_ttl(claim.expires_at, self._clock.now()),
        )
