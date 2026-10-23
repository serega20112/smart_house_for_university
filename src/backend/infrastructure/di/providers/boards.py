"""Платы аккаунта: список, взятие, сопряжение, отзыв и смена сети."""

from __future__ import annotations

from dishka import Provider, Scope, provide

from backend.application.interface.queries.board_queries import BoardQueries
from backend.application.interface.services.board_gateway import BoardGateway
from backend.application.interface.services.clock import Clock
from backend.application.interface.unit_of_work.board_onboarding import (
    BoardOnboardingUnitOfWorkFactory,
)
from backend.application.services.board_onboarding import BoardOnboardingService
from backend.application.use_cases.boards.claim_board import ClaimBoardUseCase
from backend.application.use_cases.boards.configure_board_network import (
    ConfigureBoardNetworkUseCase,
)
from backend.application.use_cases.boards.list_boards import ListBoardsUseCase
from backend.application.use_cases.boards.list_claims import ListBoardClaimsUseCase
from backend.application.use_cases.boards.pair_board import PairBoardUseCase
from backend.application.use_cases.boards.read_board_network import ReadBoardNetworkUseCase
from backend.application.use_cases.boards.revoke_board import RevokeBoardUseCase

REQUEST = Scope.REQUEST


class BoardProvider(Provider):
    """Точки входа, которыми владелец распоряжается своими платами."""

    @provide(scope=REQUEST)
    def claim_board(self, onboarding: BoardOnboardingService) -> ClaimBoardUseCase:
        """Собирает взятие объявленной платы."""
        return ClaimBoardUseCase(onboarding)

    @provide(scope=REQUEST)
    def pair_board(self, onboarding: BoardOnboardingService) -> PairBoardUseCase:
        """Собирает ручное сопряжение платы."""
        return PairBoardUseCase(onboarding)

    @provide(scope=REQUEST)
    def revoke_board(self, onboarding: BoardOnboardingService) -> RevokeBoardUseCase:
        """Собирает отзыв платы."""
        return RevokeBoardUseCase(onboarding)

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
