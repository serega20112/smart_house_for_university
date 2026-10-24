"""Обживание плат в одном месте.

Объявить плату, забрать её, сопрячь, перечислить и отозвать — одна жизнь из пяти
шагов, поэтому здесь один связный сервис, а не пять микроклассов, каждый из которых
открывает свою транзакцию и возвращает кортеж статуса. Чтение списка предложений
никого не удаляет: убрать просроченное — явная команда, которую запускает фоновый
процесс.
"""

from __future__ import annotations

from backend.application.dto.boards.announce_board_command import AnnounceBoardCommand
from backend.application.dto.boards.claim_board_command import ClaimBoardCommand
from backend.application.dto.boards.pair_board_command import PairBoardCommand
from backend.application.dto.views.board_view import BoardView
from backend.application.errors import (
    BoardAlreadyClaimedError,
    BoardNotFoundError,
    ClaimNotFoundError,
)
from backend.application.interfaces.queries.board_queries import BoardQueries
from backend.application.interfaces.services.boards.board_gateway import BoardGateway
from backend.application.interfaces.services.messaging.realtime_publisher import RealtimePublisher
from backend.application.interfaces.services.system.clock import Clock
from backend.application.interfaces.unit_of_work.board_onboarding import (
    BoardOnboardingUnitOfWorkFactory,
)
from backend.application.use_cases.boards.result import PairedBoard
from backend.domain.aggregates.esp_device.esp_device import EspDevice
from backend.domain.entities.esp_claim.esp_claim import EspClaim
from backend.domain.events import EventName
from backend.domain.identifiers import EspDeviceId, UserId
from backend.domain.value_objects.boards.pairing_key import PairingKey


class BoardOnboardingService:
    """Владеет всей жизнью плат системы."""

    def __init__(
        self,
        onboarding_uow: BoardOnboardingUnitOfWorkFactory,
        queries: BoardQueries,
        boards: BoardGateway,
        realtime: RealtimePublisher,
        clock: Clock,
        claim_ttl_sec: int,
    ) -> None:
        """Инициализирует сервис.

        Args:
            onboarding_uow: Фабрика транзакций над платами.
            queries: Дешёвые чтения для ответов на вопросы интерфейса.
            boards: Шлюз, знающий, подключена ли плата сейчас.
            realtime: Издатель событий в открытые соединения.
            clock: Источник текущего времени.
            claim_ttl_sec: Сколько времени предложение остаётся действительным.
        """
        self._uow = onboarding_uow
        self._queries = queries
        self._boards = boards
        self._realtime = realtime
        self._clock = clock
        self._claim_ttl_sec = claim_ttl_sec

    async def announce(self, command: AnnounceBoardCommand) -> EspClaim:
        """Публикует или обновляет предложение платы, у которой нет хозяина.

        Плата, объявившаяся снова, пока её предложение открыто, получает то же
        предложение: код, который человек видит на экране, остаётся кодом, о котором
        просит плата, вместо гонки двух невидимых токенов.

        Args:
            command: Ключ и код, которые плата предъявила.

        Returns:
            EspClaim: Открытое предложение этой платы.
        """
        key = PairingKey(command.device_key)
        now = self._clock.now()
        async with self._uow() as uow:
            current = await uow.claims.current_for(key.value)
            if current is not None and current.is_valid_at(now):
                return current
            label = command.label or EspClaim.label_from_key(key)
            offer = EspClaim.announce(key, label, now, self._claim_ttl_sec)
            await uow.claims.add(offer)
            await uow.commit()
        await self._realtime.broadcast(
            EventName.BOARD_ANNOUNCEMENT_PUBLISHED,
            {
                "label": offer.label,
                "claim_token": offer.claim_token,
                "expires_at": offer.expires_at.isoformat(),
            },
        )
        return offer

    async def claim(self, user_id: UserId, command: ClaimBoardCommand) -> BoardView:
        """Забирает объявленную плату за аккаунтом.

        Забирание — единственный способ, которым плата обретает владельца, и оно пишет
        предложение вместе с платой в одной транзакции, поэтому следующий дозвон платы
        уже разрешается в аккаунт.

        Args:
            user_id: Аккаунт, который забирает плату.
            command: Токен предложения и выбранное имя.

        Returns:
            BoardView: Плата, которая теперь принадлежит аккаунту.

        Raises:
            ClaimNotFoundError: Когда токен неизвестен.
            ClaimExpiredError: Когда предложение больше недействительно.
            BoardAlreadyClaimedError: Когда плату раньше забрал кто-то другой.
        """
        now = self._clock.now()
        async with self._uow() as uow:
            offer = await uow.claims.open_with_token(command.claim_token)
            if offer is None:
                raise ClaimNotFoundError(command.claim_token)
            offer.refuse_if_not_usable(now)
            taken = await uow.claims.take(offer.id, user_id)
            if not taken:
                raise BoardAlreadyClaimedError()
            board = EspDevice.pair(
                user_id=user_id,
                name=command.name,
                pairing_key=offer.device_key,
                paired_at=now,
            )
            await uow.boards.add(board)
            await uow.commit()
        await self._realtime.publish(
            user_id,
            EventName.BOARD_PAIRED,
            {"board_id": str(board.id), "name": board.name},
        )
        return BoardView(id=board.id, name=board.name, online=False, last_seen_at=None)

    async def pair(self, user_id: UserId, command: PairBoardCommand) -> PairedBoard:
        """Сопрягает плату из интерфейса и ровно один раз отдаёт её ключ.

        Args:
            user_id: Аккаунту, которому будет принадлежать плата.
            command: Имя платы и необязательный выбранный человеком ключ.

        Returns:
            PairedBoard: Плата вместе с ключом, который она должна предъявлять.

        Raises:
            InvalidPairingKeyError: Когда переданный ключ неподходящей формы.
        """
        key = (
            PairingKey.generate()
            if command.pairing_key is None
            else PairingKey(command.pairing_key)
        )
        async with self._uow() as uow:
            board = EspDevice.pair(
                user_id=user_id,
                name=command.name,
                pairing_key=key,
                paired_at=self._clock.now(),
            )
            await uow.boards.add(board)
            await uow.commit()
        return PairedBoard(
            board=BoardView(id=board.id, name=board.name, online=False, last_seen_at=None),
            pairing_key=key.value,
        )

    async def revoke(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Убирает плату из аккаунта.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.

        Raises:
            BoardNotFoundError: Когда такой платы у аккаунта нет.
        """
        async with self._uow() as uow:
            removed = await uow.boards.delete(user_id, board_id)
            if removed:
                await uow.commit()
        if not removed:
            raise BoardNotFoundError(board_id)

    async def purge_expired_claims(self) -> int:
        """Убирает предложения, которые перестали быть действительными.

        Это явная команда фонового процесса, поэтому простое перечисление
        предложений в базе ничего не меняет.

        Returns:
            int: Число убранных предложений.
        """
        async with self._uow() as uow:
            removed = await uow.claims.delete_expired(self._clock.now())
            if removed:
                await uow.commit()
        return removed
