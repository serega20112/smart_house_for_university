"""Шлюз к железу для процесса, который не держит сокетов плат.

Рабочий выполняет автоматику и сценарии, но WebSocket-сервер плат принадлежит процессу
API. Поэтому команды этого шлюза не идут в сокет напрямую, а публикуются в Redis-шину,
где их исполняет сервер плат и возвращает ответ. Доступность платы читается из того же
разделённого реестра присутствия, что и в процессе API, — оба видят одно и то же.

Ручной путь из интерфейса этим шлюзом не пользуется: там соединение рядом, и команда
уходит напрямую, быстрее и без лишних сериализаций.
"""

from __future__ import annotations

import time
from uuid import uuid4

from backend.application.dto.boards.board_command_result import BoardCommandResult
from backend.application.interfaces.services.boards.board_gateway import BoardGateway
from backend.domain.identifiers import EspDeviceId, UserId
from backend.domain.value_objects.boards.network_profile import NetworkProfile
from backend.infrastructure.brokers.board_presence import RedisBoardPresence
from backend.infrastructure.brokers.command_bus import (
    REQUEST_STATE,
    SET_NETWORK,
    SET_RELAY,
    BoardCommand,
    RedisBoardCommandBus,
)
from backend.infrastructure.system import metrics


class RemoteBoardGateway(BoardGateway):
    """Шлёт команды платам через шину и читает их доступность из Redis.

    Args:
        bus: Шина команд, ведущая к процессу с сервером плат.
        presence: Разделённый реестр подключённых плат.
    """

    def __init__(self, bus: RedisBoardCommandBus, presence: RedisBoardPresence) -> None:
        """Инициализирует шлюз.

        Args:
            bus: Шина команд, ведущая к процессу с сервером плат.
            presence: Разделённый реестр подключённых плат.
        """
        self._bus = bus
        self._presence = presence

    async def set_relay(
        self, user_id: UserId, board_id: EspDeviceId, channel: int, energized: bool
    ) -> BoardCommandResult:
        """Переключает реле через шину и ждёт подтверждения.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.
            channel: Физический канал реле.
            energized: True замкнуть контакт, False разомкнуть.

        Returns:
            BoardCommandResult: Ответ платы, вернувшийся из сервера плат.
        """
        command = BoardCommand(
            command_id=uuid4().hex,
            user_id=user_id,
            board_id=board_id,
            kind=SET_RELAY,
            channel=channel,
            energized=energized,
        )
        started = time.perf_counter()
        result = await self._bus.execute(command)
        metrics.record_board_command(result.outcome, time.perf_counter() - started)
        return result

    async def request_state(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Просит плату прислать заново всё известное ей, не дожидаясь ответа.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.
        """
        await self._bus.notify(
            BoardCommand(
                command_id=uuid4().hex,
                user_id=user_id,
                board_id=board_id,
                kind=REQUEST_STATE,
            )
        )

    async def set_network(
        self, user_id: UserId, board_id: EspDeviceId, profile: NetworkProfile
    ) -> BoardCommandResult:
        """Сообщает плате сеть через шину и ждёт подтверждения.

        Пароль сети в кадр не попадает: он уходит в короткоживущий ключ, а команда
        называет его своим идентификатором. Шина не шифруется, поэтому секрет в
        общем канале лежал бы нараспашку.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.
            profile: Сеть, которую должна использовать плата.

        Returns:
            BoardCommandResult: Ответ платы, вернувшийся из сервера плат.
        """
        command = BoardCommand(
            command_id=uuid4().hex,
            user_id=user_id,
            board_id=board_id,
            kind=SET_NETWORK,
            network=BoardCommand.network_of(profile),
            secret=profile.password,
        )
        started = time.perf_counter()
        result = await self._bus.execute(command)
        metrics.record_board_command(result.outcome, time.perf_counter() - started)
        return result

    async def is_connected(self, user_id: UserId, board_id: EspDeviceId) -> bool:
        """Сообщает, держит ли плата соединение сейчас, по общему реестру.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.

        Returns:
            bool: True, когда плата подключена в этот момент.
        """
        return await self._presence.is_connected(user_id, board_id)

    async def board_for(self, user_id: UserId) -> EspDeviceId | None:
        """Возвращает единственную подключённую плату аккаунта из общего реестра.

        Args:
            user_id: Владелец плат.

        Returns:
            EspDeviceId | None: Идентификатор платы, которой приказывать, или None,
            когда у аккаунта не ровно одна подключённая плата.
        """
        return await self._presence.board_for(user_id)
