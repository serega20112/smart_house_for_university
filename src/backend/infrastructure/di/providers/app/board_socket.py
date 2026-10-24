"""Плата: транспорт, допуск, разбор её сообщений и жизненный цикл от ключа до дома."""

from __future__ import annotations

from collections.abc import AsyncIterator

from dishka import AsyncContainer, Provider, Scope, provide

from backend.application.interfaces.queries.board_queries import BoardQueries
from backend.application.interfaces.services.boards.board_announcer import BoardAnnouncer
from backend.application.interfaces.services.boards.board_gateway import BoardGateway
from backend.application.interfaces.services.boards.board_report import BoardReport
from backend.application.interfaces.services.messaging.realtime_publisher import RealtimePublisher
from backend.application.interfaces.services.system.clock import Clock
from backend.application.interfaces.unit_of_work.board_onboarding import (
    BoardOnboardingUnitOfWorkFactory,
)
from backend.application.services.board_onboarding import BoardOnboardingService
from backend.application.use_cases.boards.admit_board import AdmitBoardUseCase
from backend.application.use_cases.boards.route_board_message import RouteBoardMessageUseCase
from backend.config.settings import Settings
from backend.infrastructure.esp.adapters import BoardGatewayAdapter
from backend.infrastructure.esp.announcement import DeferredBoardAnnouncer
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
        )
        await connection.start()
        yield connection
        await connection.stop()

    @provide(scope=APP)
    def board_gateway(self, connection: EspConnection) -> BoardGateway:
        """Собирает фасад, через который прикладной слой трогает железо."""
        return BoardGatewayAdapter(connection)

    @provide(scope=APP)
    def board_onboarding(
        self,
        uow: BoardOnboardingUnitOfWorkFactory,
        queries: BoardQueries,
        boards: BoardGateway,
        realtime: RealtimePublisher,
        clock: Clock,
        settings: Settings,
    ) -> BoardOnboardingService:
        """Собирает жизненный цикл плат системы."""
        return BoardOnboardingService(
            onboarding_uow=uow,
            queries=queries,
            boards=boards,
            realtime=realtime,
            clock=clock,
            claim_ttl_sec=settings.board_claim_ttl_sec,
        )
