"""Забрать объявленную плату за аккаунта."""

from __future__ import annotations

from backend.application.dto.boards.claim_board_command import ClaimBoardCommand
from backend.application.services.board_onboarding import BoardOnboardingService
from backend.domain.identifiers import UserId
from backend.domain.value_objects.boards.board_view import BoardView


class ClaimBoardUseCase:
    """Закрывает предложение и делает плату собственностью аккаунта."""

    def __init__(self, onboarding: BoardOnboardingService) -> None:
        """Собирает сценарий взятия платы.

        Args:
            onboarding: Жизненный цикл плат системы.
        """
        self._onboarding = onboarding

    async def execute(self, user_id: UserId, command: ClaimBoardCommand) -> BoardView:
        """Забирает плату по токену предложения.

        Args:
            user_id: Владелец, который берёт плату.
            command: Токен предложения и выбранное имя.

        Returns:
            BoardView: Плата, которая теперь принадлежит аккаунту.

        Raises:
            ClaimNotFoundError: Когда токен неизвестен.
            ClaimExpiredError: Когда предложение истекло.
            BoardAlreadyClaimedError: Когда плату раньше забрал кто-то другой.
        """
        return await self._onboarding.claim(user_id, command)
