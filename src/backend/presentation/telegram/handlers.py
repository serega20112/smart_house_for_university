"""Telegram interface.

The bot never talks to the hardware: it forwards the message text to the same
use case the web interface uses and returns the rendered answer.

A chat is bound to an account, so every command issued from Telegram is executed
inside the scope of that one user.
"""

from __future__ import annotations

from backend.application.dto.command import ProcessUserCommand
from backend.application.dto.user import AuthenticateUserCommand
from backend.application.use_cases.command import ProcessUserCommandUseCase
from backend.application.use_cases.user import AuthenticateUserUseCase
from backend.domain.exceptions import InvalidCredentialsError
from backend.presentation.api.responses import CommandResponse
from backend.presentation.telegram.links import CHAT_EMAIL

NOT_AUTHORIZED = "Сначала авторизуйтесь: /login <email> <пароль>"


class TelegramCommandsHandler:
    """Adapts Telegram messages to the shared command pipeline."""

    def __init__(
        self,
        process_user_command: ProcessUserCommandUseCase,
        authenticate_user: AuthenticateUserUseCase,
    ) -> None:
        """Initialize the handler.

        Args:
            process_user_command: Use case executing free-form commands.
            authenticate_user: Use case binding a chat to an account.

        Returns:
            None.
        """
        self._process_user_command = process_user_command
        self._authenticate_user = authenticate_user
        self._chats: dict[int, object] = {}

    async def handle(self, chat_id: int, text: str) -> str:
        """Process an incoming message and return the reply text.

        Args:
            chat_id: Identifier of the chat the message came from.
            text: Raw command text.

        Returns:
            str: Reply text.
        """
        credentials = _login_arguments(text)
        if credentials is not None:
            return await self._login(chat_id, credentials)
        user_id = self._chats.get(chat_id)
        if user_id is None:
            return NOT_AUTHORIZED
        result = await self._process_user_command.execute(
            user_id, ProcessUserCommand(text=text)
        )
        return CommandResponse.from_result(result).message

    async def _login(self, chat_id: int, credentials: tuple[str, str]) -> str:
        """Bind a chat to an account.

        Args:
            chat_id: Identifier of the chat the message came from.
            credentials: Login and password taken from the message.

        Returns:
            str: Reply text.
        """
        email, password = credentials
        try:
            session = await self._authenticate_user.execute(
                AuthenticateUserCommand(email=email, password=password)
            )
        except InvalidCredentialsError:
            return "Неверный email или пароль."
        self._chats[chat_id] = session.user_id
        return f"Готово, {session.user.display_name}. Команды работают."


def _login_arguments(text: str) -> tuple[str, str] | None:
    parts = text.split()
    if len(parts) != 3 or parts[0] != CHAT_EMAIL:
        return None
    return parts[1], parts[2]
