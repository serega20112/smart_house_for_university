"""Допуск платы, которая дозвонилась: владелец, объявление или отказ.

Решение принимает прикладной слой, а не транспорт: неизвестный ключ — это плата без
хозяина, даже если её собственная флешка утверждает обратное, и объявлять плату нужно
через тот же сервис, который публикует её в интерфейс.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

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
    BoardOnboardingUnitOfWork,
    BoardOnboardingUnitOfWorkFactory,
)
from backend.domain.entities.boards.board_network import BoardNetwork
from backend.domain.exceptions import DomainError, InvalidNetworkProfileError
from backend.domain.identifiers import EspDeviceId, UserId
from backend.domain.policies.board_admission import AdmissionKind, BoardAdmissionPolicy
from backend.domain.value_objects.boards.network_profile import NetworkProfile

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
            await self._remember_network(uow, board.id, board.user_id, greeting, now)
            await uow.commit()
            return BoardOwner(user_id=board.user_id, board_id=board.id)

    async def _remember_network(
        self,
        uow: BoardOnboardingUnitOfWork,
        board_id: EspDeviceId,
        user_id: UserId,
        greeting: BoardGreeting,
        now: datetime,
    ) -> None:
        """Запоминает адрес сервера и сеть, о которых плата сообщила сама.

        Плата, настроенная через собственную точку доступа, никогда не проходила через
        редактор сети, и сервер не знал бы её адреса, пока плата сама не назвала его в
        handshake. Здесь этот адрес оседает в хранилище, чтобы интерфейс открыл форму
        сети уже заполненной, а не заставлял человека вбивать то, что плата знает.

        Пароль сети плата не сообщает и не может сообщить: он остаётся в её памяти, а
        здесь бережно сохраняется прежний, если он уже был записан.

        Args:
            uow: Граница транзакции плат.
            board_id: Идентификатор платы.
            user_id: Владелец платы.
            greeting: Приветствие с адресом сервера и сетью.
            now: Момент handshake.
        """
        reported = _reported_profile(greeting)
        if reported is None:
            return
        existing = await uow.networks.get(board_id)
        if existing is not None and _same_endpoint(existing.profile, reported):
            return
        password = existing.profile.password if existing is not None else ""
        profile = replace(reported, password=password)
        await uow.networks.save(
            BoardNetwork(
                board_id=board_id,
                user_id=user_id,
                profile=profile,
                updated_at=now,
            )
        )

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
        device_key = greeting.pairing_key
        if not device_key:
            return None
        try:
            claim = await self._announcer.announce(
                AnnounceBoardCommand(device_key=device_key, label=greeting.label)
            )
        except (DomainError, ApplicationError):
            return None
        return BoardOffer(
            label=claim.label,
            ttl_sec=self._policy.offer_ttl(claim.expires_at, self._clock.now()),
        )


def _reported_profile(greeting: BoardGreeting) -> NetworkProfile | None:
    """Строит профиль из того, что плата сообщила о себе, или None, если нечего строить.

    Пароль здесь всегда пустой: плата его не передаёт. Вызывающий подставит прежний.

    Args:
        greeting: Приветствие платы.

    Returns:
        NetworkProfile | None: Профиль сети или None, когда плата не назвала достаточно,
            чтобы собрать годный профиль.
    """
    if not (greeting.ssid and greeting.server_host and greeting.socket_path):
        return None
    if greeting.server_port <= 0 or greeting.socket_port <= 0:
        return None
    try:
        return NetworkProfile(
            ssid=greeting.ssid,
            password="",
            host=greeting.server_host,
            server_port=greeting.server_port,
            socket_port=greeting.socket_port,
            socket_path=greeting.socket_path or "",
        )
    except InvalidNetworkProfileError:
        return None


def _same_endpoint(first: NetworkProfile, second: NetworkProfile) -> bool:
    """Совпадают ли два профиля по всем полям, кроме пароля.

    Нужна, чтобы не переписывать строку сети на каждом handshake: плата докладывает
    одни и те же значения при каждом переподключении.

    Args:
        first: Сохранённый профиль.
        second: Профиль, который сообщила плата сейчас.

    Returns:
        bool: True, когда менять нечего.
    """
    return (
        first.ssid == second.ssid
        and first.host == second.host
        and first.server_port == second.server_port
        and first.socket_port == second.socket_port
        and first.socket_path == second.socket_path
    )
