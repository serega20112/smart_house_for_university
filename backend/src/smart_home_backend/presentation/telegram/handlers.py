"""Telegram interface.

The bot never talks to the hardware: it forwards the message text to the same
use case the web interface uses and returns the rendered answer.
"""

from __future__ import annotations

from smart_home_backend.application.dto.command import ProcessUserCommand
from smart_home_backend.application.use_cases.command import ProcessUserCommandUseCase
from smart_home_backend.presentation.api.responses import CommandResponse


class TelegramCommandsHandler:
    """Adapts Telegram messages to the shared command pipeline."""

    def __init__(self, process_user_command: ProcessUserCommandUseCase) -> None:
        """Initialize the handler.

        Args:
            process_user_command: Use case executing free-form commands.

        Returns:
            None.
        """
        self._process_user_command = process_user_command

    async def handle(self, chat_id: int, text: str) -> str:
        """Process an incoming message and return the reply text.

        Args:
            chat_id: Identifier of the chat the message came from.
            text: Raw command text.

        Returns:
            str: Reply text.
        """
        result = await self._process_user_command.execute(ProcessUserCommand(text=text))
        return CommandResponse.from_result(result).message
