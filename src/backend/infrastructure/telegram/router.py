"""Turning an incoming message into a command.

This module owns the transport of the conversation and nothing else. It resolves
which account a chat belongs to, recognizes the one time link token, and hands
the text to the two callables the composition root supplies: one that produces
the wording for a linked account, and one that produces the wording for somebody
who has to link first.

Every user facing string therefore lives in presentation, where the interface
language is known, and this module only decides which of the two paths a message
takes.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from backend.domain.identifiers import UserId
from backend.infrastructure.logging import get_logger
from backend.infrastructure.redis.chat_sessions import RedisChatSessionStore
from backend.infrastructure.telegram.linking import TelegramLinkTokenIssuer

log = get_logger("telegram.router")

InstructionComposer = Callable[[], Awaitable[str]]
CommandRunner = Callable[[UserId, str], Awaitable[str]]

LINK_PREFIX = "link:"


@dataclass(frozen=True, slots=True)
class TelegramRouting:
    """The two callables the composition root supplies.

    Args:
        unlinked_instruction: Wording telling somebody how to link their account.
        run_command: Runs a command for a linked account and returns the answer.

    Returns:
        None.
    """

    unlinked_instruction: InstructionComposer
    run_command: CommandRunner


class TelegramMessageRouter:
    """Routes an incoming message to the right composer.

    Args:
        sessions: Chats linked to accounts.
        links: Issuer and resolver of the one time link tokens.
        routing: The two callables the composition root supplies.

    Returns:
        None.
    """

    def __init__(
        self,
        sessions: RedisChatSessionStore,
        links: TelegramLinkTokenIssuer,
        routing: TelegramRouting,
    ) -> None:
        """Initialize the router.

        Args:
            sessions: Chats linked to accounts.
            links: Issuer and resolver of the one time link tokens.
            routing: The two callables the composition root supplies.

        Returns:
            None.
        """
        self._sessions = sessions
        self._links = links
        self._routing = routing

    async def handle(self, chat_id: int, text: str) -> str:
        """Answer one message.

        Args:
            chat_id: Telegram chat the message arrived in.
            text: Raw message.

        Returns:
            str: Answer to send back into the same chat.
        """
        token = _token_of(text)
        if token is not None:
            return await self._link(chat_id, token)
        user_id = await self._sessions.user_of(chat_id)
        if user_id is None:
            return await self._routing.unlinked_instruction()
        return await self._routing.run_command(user_id, text)

    async def _link(self, chat_id: int, token: str) -> str:
        user_id = self._links.resolve(token)
        if user_id is None:
            log.info("telegram.link_token_refused", chat_id=chat_id)
            return await self._routing.unlinked_instruction()
        await self._sessions.bind(chat_id, user_id)
        log.info("telegram.chat_linked", chat_id=chat_id, user=str(user_id))
        return await self._routing.run_command(user_id, "")


def _token_of(text: str) -> str | None:
    stripped = text.strip()
    if not stripped.startswith(LINK_PREFIX):
        return None
    return stripped[len(LINK_PREFIX) :].strip() or None
