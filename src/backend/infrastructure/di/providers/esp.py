"""Плата: WebSocket-транспорт, два фасада над ним и её жизненный цикл."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from dishka import AsyncContainer, Provider, Scope, provide

from backend.application.dto.boards.announce_board_command import AnnounceBoardCommand
from backend.application.interface.queries.board_queries import BoardQueries
from backend.application.interface.services.board_gateway import BoardGateway
from backend.application.interface.services.board_report import BoardReport
from backend.application.interface.services.clock import Clock
from backend.application.interface.services.realtime_publisher import RealtimePublisher
from backend.application.interface.unit_of_work.board_onboarding import (
    BoardOnboardingUnitOfWorkFactory,
)
from backend.application.services.board_onboarding import BoardOnboardingService
from backend.config.settings import Settings
from backend.domain.aggregates.esp_claim.esp_claim import EspClaim
from backend.infrastructure.esp.adapters import BoardGatewayAdapter
from backend.infrastructure.esp.connection import EspConnection
from backend.infrastructure.esp.onboarding import (
    AnnounceBoard,
    BoardOnboardingGateway,
)

APP = Scope.APP


class EspProvider(Provider):
    """Транспорт плат, шлюз сопряжения и жизненный цикл платы от ключа до дома."""

    @provide(scope=APP)
    def announce_board(self, container: AsyncContainer) -> AnnounceBoard:
        """Собирает вызываемое, которое публикует плату без владельца.

        Сервис берётся из контейнера в момент вызова: транспорт узнаёт о плате
        раньше, чем контейнер успевает собрать весь её жизненный цикл, и этот
        разрыв заполняет только отложенная отправка запроса.
        """
        return _publish_announcement(container)

    @provide(scope=APP)
    def onboarding_gateway(
        self,
        uow: BoardOnboardingUnitOfWorkFactory,
        announce: AnnounceBoard,
        clock: Clock,
    ) -> BoardOnboardingGateway:
        """Собирает операции, которые поднимает handshake платы."""
        return BoardOnboardingGateway(uow, announce, clock)

    @provide(scope=APP)
    def connection(
        self,
        report: BoardReport,
        onboarding: BoardOnboardingGateway,
        settings: Settings,
    ) -> EspConnection:
        """Собирает WebSocket-сервер, на который звонят платы."""
        return EspConnection(
            report=report,
            onboarding=onboarding,
            host=settings.app_host,
            port=settings.board_socket_port,
            path=settings.board_socket_path,
            command_timeout_sec=settings.board_command_timeout_sec,
            handshake_timeout_sec=settings.board_handshake_timeout_sec,
            ping_interval_sec=settings.board_ping_interval_sec,
            ping_timeout_sec=settings.board_ping_timeout_sec,
        )

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


def _publish_announcement(
    container: AsyncContainer,
) -> Callable[[AnnounceBoardCommand], Awaitable[EspClaim]]:
    """Возвращает вызываемое, публикующее предложение незнакомой платы."""

    async def announce(command: AnnounceBoardCommand) -> EspClaim:
        """Публикует или обновляет предложение платы с этим ключом."""
        service = await container.get(BoardOnboardingService)
        return await service.announce(command)

    return announce
