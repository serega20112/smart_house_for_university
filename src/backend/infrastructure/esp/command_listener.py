"""Исполнение команд железа, пришедших от других процессов через Redis.

WebSocket-сервер плат живёт только в процессе API, поэтому команды, которые публикует
рабочий (автоматика и сценарии), должен кто-то превращать в настоящие кадры платам. Этот
слушатель читает канал команд, вызывает транспорт ровно так же, как это делает ручной
путь из интерфейса, и возвращает ответ в канал команды, где его дожидается отправитель.

Каждая команда исполняется своей задачей: медленное подтверждение одной платы не
задерживает очередь остальных, а сбой разбора отдельного кадра не роняет весь слушатель.
Секрет команды слушатель забирает из хранилища одноразово, поэтому пароль сети не
лежит в общем канале и не достаётся тому, кто прочитает его вторым.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress

from backend.application.dto.boards.board_command_reason import BoardCommandReason
from backend.application.dto.boards.board_command_result import BoardCommandResult
from backend.infrastructure.brokers.command_bus import (
    REQUEST_STATE,
    SET_NETWORK,
    SET_RELAY,
    BoardCommand,
    RedisBoardCommandBus,
)
from backend.infrastructure.esp.connection import EspConnection
from backend.infrastructure.system.logging import get_logger

log = get_logger("esp.command_listener")


class BoardCommandListener:
    """Читает канал команд и исполняет их на локальном соединении с платами.

    Args:
        bus: Шина, из которой читаются команды и в которую возвращаются ответы.
        connection: Транспорт, действительно держащий сокеты плат.
    """

    def __init__(self, bus: RedisBoardCommandBus, connection: EspConnection) -> None:
        """Инициализирует слушатель.

        Args:
            bus: Шина, из которой читаются команды и в которую возвращаются ответы.
            connection: Транспорт, действительно держащий сокеты плат.
        """
        self._bus = bus
        self._connection = connection
        self._inflight: set[asyncio.Task[None]] = set()

    async def run(self) -> None:
        """Читает команды и запускает каждую отдельной задачей, пока не отменён.

        Обрыв соединения с Redis прерывает чтение и записывается в журнал, но не
        роняет задачу молча: слушатель завершается аккуратно, а не оставляет
        неизвлечённое исключение фоновой задачи.

        Raises:
            asyncio.CancelledError: Когда процесс гасит слушателя на остановке.
        """
        try:
            async for command in self._bus.commands():
                task = asyncio.create_task(self._handle(command))
                self._inflight.add(task)
                task.add_done_callback(self._inflight.discard)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            log.error("esp.command_listener.stopped", error=str(error))

    async def shutdown(self) -> None:
        """Отменяет недоисполненные команды на остановке процесса."""
        for task in list(self._inflight):
            task.cancel()
        for task in list(self._inflight):
            with suppress(asyncio.CancelledError):
                await task

    async def _handle(self, command: BoardCommand) -> None:
        """Исполняет одну команду и возвращает ответ, кроме запроса состояния.

        Args:
            command: Команда, пришедшая из канала.
        """
        if command.kind == SET_RELAY:
            await self._set_relay(command)
        elif command.kind == SET_NETWORK:
            await self._set_network(command)
        elif command.kind == REQUEST_STATE:
            await self._connection.request_state(command.user_id, command.board_id)
        else:
            await self._bus.publish_result(
                command.command_id,
                BoardCommandResult(accepted=False, reason=BoardCommandReason.UNKNOWN_COMMAND),
            )

    async def _set_relay(self, command: BoardCommand) -> None:
        """Переключает канал реле и возвращает ответ платы."""
        if command.channel is None or command.energized is None:
            await self._bus.publish_result(
                command.command_id,
                BoardCommandResult(accepted=False, reason=BoardCommandReason.UNKNOWN_COMMAND),
            )
            return
        result = await self._connection.set_relay(
            command.user_id, command.board_id, command.channel, command.energized
        )
        await self._bus.publish_result(command.command_id, result)

    async def _set_network(self, command: BoardCommand) -> None:
        """Меняет сеть платы и возвращает ответ, когда профиль собран.

        Пароль приходит не в кадре, а из короткоживущего ключа: без него профиль
        неполон, и команда отклоняется с отдельной причиной.
        """
        password = await self._bus.take_secret(command.command_id)
        if password is None:
            await self._bus.publish_result(
                command.command_id,
                BoardCommandResult(accepted=False, reason=BoardCommandReason.SECRET_MISSING),
            )
            return
        profile = command.network_profile(password)
        if profile is None:
            await self._bus.publish_result(
                command.command_id,
                BoardCommandResult(accepted=False, reason=BoardCommandReason.INVALID_NETWORK),
            )
            return
        result = await self._connection.set_network(command.user_id, command.board_id, profile)
        await self._bus.publish_result(command.command_id, result)
