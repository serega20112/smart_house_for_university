"""Транспорт плат и всё, что происходит вокруг его соединения (процесс API).

WebSocket-сервер плат заводится ровно в одном процессе — том, что обслуживает запросы
человека. Рабочий этот провайдер не получает вовсе: он говорит с платами через шину
команд, а не через собственный сокет, и потому не может случайно поднять второй сервер
на том же порту.

Здесь собираются допуск платы, разбор её сообщений, локальный шлюз к железу и слушатель
команд, превращающий приказы рабочего в настоящие кадры платам. Жизненный цикл плат и
общий реестр присутствия живут в `board_coordination`, раз они нужны обоим процессам.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress

from dishka import AsyncContainer, Provider, Scope, provide

from backend.application.interfaces.services.boards.board_announcer import BoardAnnouncer
from backend.application.interfaces.services.boards.board_gateway import BoardGateway
from backend.application.interfaces.services.boards.board_report import BoardReport
from backend.application.interfaces.services.system.clock import Clock
from backend.application.interfaces.unit_of_work.board_onboarding import (
    BoardOnboardingUnitOfWorkFactory,
)
from backend.application.use_cases.boards.admit_board import AdmitBoardUseCase
from backend.application.use_cases.boards.route_board_message import RouteBoardMessageUseCase
from backend.config.settings import Settings
from backend.infrastructure.brokers.board_presence import RedisBoardPresence
from backend.infrastructure.brokers.command_bus import RedisBoardCommandBus
from backend.infrastructure.esp.adapters import BoardGatewayAdapter
from backend.infrastructure.esp.announcement import DeferredBoardAnnouncer
from backend.infrastructure.esp.command_listener import BoardCommandListener
from backend.infrastructure.esp.connection import EspConnection

APP = Scope.APP


class BoardSocketProvider(Provider):
    """Транспорт плат и всё, что происходит вокруг его соединения."""

    @provide(scope=APP)
    def announcer(self, container: AsyncContainer) -> BoardAnnouncer:
        """Собирает отложенное объявление платы.

        Сервис берётся из контейнера в момент вызова: транспорт узнаёт о плате раньше,
        чем контейнер успевает собрать весь её жизненный цикл, и этот разрыв заполняет
        только отложенная просьба.
        """
        return DeferredBoardAnnouncer(container)

    @provide(scope=APP)
    def admit_board(
        self,
        uow: BoardOnboardingUnitOfWorkFactory,
        announcer: BoardAnnouncer,
        clock: Clock,
    ) -> AdmitBoardUseCase:
        """Собирает допуск платы, которая дозвонилась."""
        return AdmitBoardUseCase(uow, announcer, clock)

    @provide(scope=APP)
    def route_board_message(self, report: BoardReport) -> RouteBoardMessageUseCase:
        """Собирает разбор сообщений платы."""
        return RouteBoardMessageUseCase(report)

    @provide(scope=APP)
    async def connection(
        self,
        report: BoardReport,
        admission: AdmitBoardUseCase,
        router: RouteBoardMessageUseCase,
        presence: RedisBoardPresence,
        settings: Settings,
    ) -> AsyncIterator[EspConnection]:
        """Собирает WebSocket-сервер, поднимает его и гасит вместе с процессом.

        Returns:
            AsyncIterator[EspConnection]: Запущенное соединение с платами.

        Yields:
            EspConnection: Сервер, который уже слушает платы.
        """
        connection = EspConnection(
            report=report,
            admission=admission,
            router=router,
            host=settings.app_host,
            port=settings.board_socket_port,
            path=settings.board_socket_path,
            command_timeout_sec=settings.board_command_timeout_sec,
            handshake_timeout_sec=settings.board_handshake_timeout_sec,
            ping_interval_sec=settings.board_ping_interval_sec,
            ping_timeout_sec=settings.board_ping_timeout_sec,
            presence=presence,
        )
        await connection.start()
        yield connection
        await connection.stop()

    @provide(scope=APP)
    def board_gateway(
        self, connection: EspConnection, presence: RedisBoardPresence
    ) -> BoardGateway:
        """Собирает фасад, через который прикладной слой этого процесса трогает железо."""
        return BoardGatewayAdapter(connection, presence)

    @provide(scope=APP)
    async def command_listener(
        self, bus: RedisBoardCommandBus, connection: EspConnection
    ) -> AsyncIterator[BoardCommandListener]:
        """Запускает слушатель команд рабочего и гасит его вместе с процессом.

        Yields:
            BoardCommandListener: Слушатель, уже читающий канал команд.
        """
        listener = BoardCommandListener(bus, connection)
        task = asyncio.create_task(listener.run())
        try:
            yield listener
        finally:
            task.cancel()
            await listener.shutdown()
            with suppress(asyncio.CancelledError):
                await task
