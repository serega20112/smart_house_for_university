"""Сопрясть плату с аккаунтом вручную."""

from __future__ import annotations

from backend.application.dto.boards.pair_board_command import PairBoardCommand
from backend.application.services.board_onboarding import BoardOnboardingService
from backend.application.use_cases.boards.result import PairedBoard
from backend.domain.identifiers import UserId


class PairBoardUseCase:
    """Заводит плату в аккаунт и отдаёт ключ ровно один раз."""

    def __init__(self, onboarding: BoardOnboardingService) -> None:
        """Собирает сценарий сопряжения.

        Args:
            onboarding: Жизненный цикл плат системы.
        """
        self._onboarding = onboarding

    async def execute(self, user_id: UserId, command: PairBoardCommand) -> PairedBoard:
        """Сопрягает плату с аккаунтом.

        Args:
            user_id: Владелец, которому достанется плата.
            command: Имя платы и, возможно, выбранный человеком ключ.

        Returns:
            PairedBoard: Плата вместе с ключом, который она должна предъявлять.

        Raises:
            InvalidPairingKeyError: Когда переданный ключ испорчен.
        """
        return await self._onboarding.pair(user_id, command)
