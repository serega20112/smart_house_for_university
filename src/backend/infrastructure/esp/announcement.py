"""Объявление платы, отложенное до первого handshake.

Транспорт плат получает сервис объявления, а сервис объявления получает транспорт:
BoardOnboardingService знает шлюз к плате, чтобы подтвердить взятие. Развязывает этот
круг только отложенная просьба к контейнеру — она случается, когда приложение уже
собрано и сервер плат запущен.
"""

from __future__ import annotations

from dishka import AsyncContainer

from backend.application.dto.boards.announce_board_command import AnnounceBoardCommand
from backend.application.services.board_onboarding import BoardOnboardingService
from backend.domain.entities.esp_claim.esp_claim import EspClaim


class DeferredBoardAnnouncer:
    """Публикует плату через сервис, которого ещё нет в момент сборки транспорта."""

    def __init__(self, container: AsyncContainer) -> None:
        """Инициализирует отложенное объявление.

        Args:
            container: Граф зависимостей запущенного процесса.
        """
        self._container = container

    async def announce(self, command: AnnounceBoardCommand) -> EspClaim:
        """Публикует или обновляет предложение платы с этим ключом.

        Args:
            command: Ключ и код, которые плата предъявила.

        Returns:
            EspClaim: Открытое предложение этой платы.
        """
        service = await self._container.get(BoardOnboardingService)
        return await service.announce(command)
