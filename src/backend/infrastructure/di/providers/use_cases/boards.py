"""Платы аккаунта: список, смена сети и чтение открытых предложений.

Жизнь платы — взятие, сопряжение и отзыв — живёт одним сервисом прикладного слоя, а не
тремя сценариями-делегатами, которые ничего бы не решали: здесь остаются только те
точки входа, у которых есть собственное чтение или собственная команда.
"""

from __future__ import annotations

from dishka import Provider, Scope, provide

from backend.application.interfaces.queries.board_queries import BoardQueries
from backend.application.interfaces.services.boards.board_gateway import BoardGateway
from backend.application.interfaces.services.system.clock import Clock
from backend.application.interfaces.unit_of_work.board_onboarding import (
    BoardOnboardingUnitOfWorkFactory,
)
from backend.application.use_cases.boards.configure_board_network import (
    ConfigureBoardNetworkUseCase,
)
from backend.application.use_cases.boards.list_boards import ListBoardsUseCase
from backend.application.use_cases.boards.list_claims import ListBoardClaimsUseCase
from backend.application.use_cases.boards.read_board_network import ReadBoardNetworkUseCase

REQUEST = Scope.REQUEST


class BoardsUseCaseProvider(Provider):
    """Точки входа, которыми владелец распоряжается своими платами."""

    @provide(scope=REQUEST)
    def list_boards(self, queries: BoardQueries, gateway: BoardGateway) -> ListBoardsUseCase:
        """Собирает список плат."""
        return ListBoardsUseCase(queries, gateway)

    @provide(scope=REQUEST)
    def list_board_claims(self, queries: BoardQueries) -> ListBoardClaimsUseCase:
        """Собирает список открытых предложений плат."""
        return ListBoardClaimsUseCase(queries)

    @provide(scope=REQUEST)
    def configure_board_network(
        self,
        onboarding_uow: BoardOnboardingUnitOfWorkFactory,
        boards: BoardGateway,
        clock: Clock,
    ) -> ConfigureBoardNetworkUseCase:
        """Собирает смену сети платы."""
        return ConfigureBoardNetworkUseCase(onboarding_uow, boards, clock)

    @provide(scope=REQUEST)
    def read_board_network(
        self, onboarding_uow: BoardOnboardingUnitOfWorkFactory
    ) -> ReadBoardNetworkUseCase:
        """Собирает чтение сети платы."""
        return ReadBoardNetworkUseCase(onboarding_uow)
