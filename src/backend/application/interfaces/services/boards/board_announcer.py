"""Порт, публикующий плату, у которой ещё нет хозяина."""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.application.dto.boards.announce_board_command import AnnounceBoardCommand
from backend.domain.entities.esp_claim.esp_claim import EspClaim


class BoardAnnouncer(ABC):
    """Объявляет найденную плату тем, кто её заберёт."""

    @abstractmethod
    async def announce(self, command: AnnounceBoardCommand) -> EspClaim:
        """Публикует или обновляет предложение платы.

        Args:
            command: Ключ и код, которые плата предъявила.

        Returns:
            EspClaim: Открытое предложение этой платы.
        """
