"""Убрать плату из аккаунта."""

from __future__ import annotations

from backend.application.services.board_onboarding import BoardOnboardingService
from backend.domain.identifiers import EspDeviceId, UserId


class RevokeBoardUseCase:
    """Прекращает владение платой."""

    def __init__(self, onboarding: BoardOnboardingService) -> None:
        """Собирает сценарий отзыва платы.

        Args:
            onboarding: Жизненный цикл плат системы.
        """
        self._onboarding = onboarding

    async def execute(self, user_id: UserId, board_id: EspDeviceId) -> None:
        """Удаляет плату из аккаунта.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.

        Raises:
            BoardNotFoundError: Когда у аккаунта нет такой платы.
        """
        await self._onboarding.revoke(user_id, board_id)
