"""Читает сеть, которую предписано использовать плате."""

from __future__ import annotations

from backend.application.errors import BoardNotFoundError
from backend.application.interfaces.unit_of_work.board_onboarding import (
    BoardOnboardingUnitOfWorkFactory,
)
from backend.domain.identifiers import EspDeviceId, UserId
from backend.domain.value_objects.boards.board_network_view import BoardNetworkView


class ReadBoardNetworkUseCase:
    """Показывает сохранённую сеть платы."""

    def __init__(self, onboarding_uow: BoardOnboardingUnitOfWorkFactory) -> None:
        """Собирает сценарий чтения сети.

        Args:
            onboarding_uow: Граница транзакции над платами.
        """
        self._uow = onboarding_uow

    async def execute(self, user_id: UserId, board_id: EspDeviceId) -> BoardNetworkView | None:
        """Возвращает сеть платы в форме для интерфейса.

        Args:
            user_id: Владелец платы.
            board_id: Идентификатор платы.

        Returns:
            BoardNetworkView | None: Сеть или None, если плату никогда не
                настраивали.

        Raises:
            BoardNotFoundError: Когда у аккаунта нет такой платы.
        """
        async with self._uow() as uow:
            board = await uow.boards.get(user_id, board_id)
            if board is None:
                raise BoardNotFoundError(board_id)
            network = await uow.networks.get(board_id)
        if network is None:
            return None
        return BoardNetworkView.of(network.board_id, network.profile, network.updated_at)
