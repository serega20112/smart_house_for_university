"""Сеанс платы: её сокет, команды в ожидании подтверждения и реестр подключённых плат.

Ключом реестра служит пара «аккаунт — плата», а не аккаунт: плат у владельца
может быть несколько, и вторая вытеснила бы первую, что и делает дом из нескольких
комнат невозможным.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import suppress

from websockets.asyncio.server import ServerConnection

from backend.domain.identifiers import EspDeviceId, UserId
from backend.infrastructure.esp import protocol
from backend.infrastructure.system.logging import get_logger

log = get_logger("esp.session")


class BoardSession:
    """Одна подключённая плата и команды, ждущие её подтверждения.

    Args:
        user_id: Владелец платы.
        board_id: Идентификатор платы.
        socket: Открытый WebSocket платы.
        counter: Источник идентификаторов, уникальных внутри этого сеанса.
    """

    def __init__(
        self,
        user_id: UserId,
        board_id: EspDeviceId,
        socket: ServerConnection,
        counter: Callable[[], str],
    ) -> None:
        """Инициализирует сеанс.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.
            socket: Открытый WebSocket платы.
            counter: Источник идентификаторов, уникальных внутри этого сеанса.
        """
        self.user_id = user_id
        self.board_id = board_id
        self.socket = socket
        self.pending: dict[str, asyncio.Future[None]] = {}
        self._counter = counter

    def next_command_id(self) -> str:
        """Возвращает идентификатор, уникальный внутри этого сеанса."""
        return self._counter()

    async def deliver(self, frame: protocol.OutboundFrame) -> bool:
        """Пишет кадр платы, не дожидаясь ответа.

        Отказ сокета превращается в False, а не в исключение: недоступность
        железа — решение вызывающей стороны, а не авария транспорта.

        Args:
            frame: Кадр, который уходит плате.

        Returns:
            bool: True, когда кадр ушёл.
        """
        try:
            await self.socket.send(frame.to_json())
        except Exception as error:
            log.warning(
                "esp.frame_delivery_failed",
                user=str(self.user_id),
                board=str(self.board_id),
                error=str(error),
            )
            return False
        return True

    async def ask(
        self,
        frame: protocol.SetRelayFrame | protocol.SetNetworkFrame,
        timeout_sec: float,
    ) -> None:
        """Пишет кадр и ждёт подтверждения с тем же идентификатором команды.

        Args:
            frame: Кадр, уже несущий идентификатор команды.
            timeout_sec: Сколько секунд ждём подтверждения.

        Raises:
            TimeoutError: Когда плата не подтвердила кадр за отведённое время.
            Exception: Когда кадр не удалось написать в сокет.
        """
        command_id = frame.command_id
        future: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        self.pending[command_id] = future
        try:
            await self.socket.send(frame.to_json())
            await asyncio.wait_for(future, timeout=timeout_sec)
        finally:
            self.pending.pop(command_id, None)

    def resolve_ack(self, command_id: str) -> None:
        """Считает команду подтверждённой, если такая ещё дожидается ответа."""
        future = self.pending.pop(command_id, None)
        if future is not None and not future.done():
            future.set_result(None)

    def cancel_pending(self) -> None:
        """Отменяет все команды, оставшиеся без подтверждения."""
        for future in self.pending.values():
            if not future.done():
                future.cancel()
        self.pending.clear()

    async def close(self) -> None:
        """Закрывает сокет платы, не превращая отказ в аварию."""
        with suppress(Exception):
            await self.socket.close()


class BoardRegistry:
    """Платы, удерживающие соединение, и счётчик их идентификаторов команд."""

    def __init__(self) -> None:
        """Инициализирует пустой реестр."""
        self._sessions: dict[tuple[UserId, EspDeviceId], BoardSession] = {}
        self._issued = 0

    def open(
        self, user_id: UserId, board_id: EspDeviceId, socket: ServerConnection
    ) -> BoardSession:
        """Регистрирует сеанс платы и возвращает его."""
        self._issued += 1
        session = BoardSession(
            user_id,
            board_id,
            socket,
            _counter_factory(board_id, self._issued),
        )
        self._sessions[(user_id, board_id)] = session
        return session

    def close(self, session: BoardSession) -> None:
        """Убирает сеанс из реестра, если там стоит всё ещё он, а не его замена.

        Плата успевает переподключиться, пока старый сокет докатывает разбор
        кадров, и удалять новый сеанс отказом старого было бы потерей платы.

        Args:
            session: Сеанс, соединение которого закрылось.
        """
        key = (session.user_id, session.board_id)
        if self._sessions.get(key) is session:
            self._sessions.pop(key, None)

    def find(self, user_id: UserId, board_id: EspDeviceId) -> BoardSession | None:
        """Возвращает сеанс платы или None, когда она не подключена."""
        return self._sessions.get((user_id, board_id))

    def is_connected(self, user_id: UserId, board_id: EspDeviceId) -> bool:
        """True, когда у этой платы держится соединение."""
        return (user_id, board_id) in self._sessions

    def board_for(self, user_id: UserId) -> EspDeviceId | None:
        """Возвращает единственную подключённую плату аккаунта.

        Запасной путь для устройства, не привязанного к плате: пока у аккаунта ровно
        одно соединение, канал однозначно принадлежит ему. При двух соединениях
        ответа нет: угадав, сервер переключил бы реле на другой стороне дома.

        Args:
            user_id: Владелец плат.

        Returns:
            EspDeviceId | None: Плата, к которой можно обратиться, или None.
        """
        connected = [board_id for owner, board_id in self._sessions if owner == user_id]
        if len(connected) != 1:
            return None
        return connected[0]

    def every(self) -> list[BoardSession]:
        """Возвращает все сеансы, чтобы закрыть их разом."""
        return list(self._sessions.values())

    def clear(self) -> None:
        """Забывает все сеансы."""
        self._sessions.clear()


def _counter_factory(board_id: EspDeviceId, start: int) -> Callable[[], str]:
    """Возвращает источник идентификаторов команд одного сеанса."""
    counter = start

    def next_id() -> str:
        """Выдаёт следующий идентификатор, уникальный внутри сеанса."""
        nonlocal counter
        counter += 1
        return f"{str(board_id)[:8]}-{counter}"

    return next_id
