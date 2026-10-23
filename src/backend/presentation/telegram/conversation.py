"""Разговор бота с одним чатом: привязка аккаунта и выполнение команды.

Решение «кому принадлежит чат» и «что на это ответить» живёт здесь, а текст
фраз приходит из того же места, что и фразы веб-интерфейса, поэтому два канала
не могут начать противоречить друг другу.
"""

from __future__ import annotations

from backend.application.errors import ApplicationError
from backend.application.services.command_dispatcher import CommandDispatcher
from backend.domain.exceptions import DomainError
from backend.domain.identifiers import UserId
from backend.infrastructure.logging import get_logger
from backend.infrastructure.redis.chat_sessions import RedisChatSessionStore
from backend.infrastructure.telegram.linking import TelegramLinkTokenIssuer
from backend.presentation.errors import describe
from backend.presentation.messages import (
    TELEGRAM_EMPTY_COMMAND,
    TELEGRAM_LINK_INSTRUCTION,
    TELEGRAM_LINKED,
    CommandReplyComposer,
)

log = get_logger("telegram.conversation")

LINK_PREFIX = "link:"


class TelegramConversation:
    """Ведёт переписку чата: привязка, команда, ответ.

    Args:
        sessions: Соответствие чатов аккаунтам.
        links: Выдающий и разбирающий токены привязки адаптер.
        dispatcher: Шина команд прикладного слоя.
        composer: Строит фразу ответа по результату команды.

    Returns:
        None.
    """

    def __init__(
        self,
        sessions: RedisChatSessionStore,
        links: TelegramLinkTokenIssuer,
        dispatcher: CommandDispatcher,
        composer: CommandReplyComposer | None = None,
    ) -> None:
        """Инициализирует разговор.

        Args:
            sessions: Соответствие чатов аккаунтам.
            links: Выдающий и разбирающий токены привязки адаптер.
            dispatcher: Шина команд прикладного слоя.
            composer: Строит фразу ответа по результату команды.

        Returns:
            None.
        """
        self._sessions = sessions
        self._links = links
        self._dispatcher = dispatcher
        self._composer = composer or CommandReplyComposer()

    async def answer(self, chat_id: int, text: str) -> str:
        """Возвращает фразу, которой бот отвечает на одно сообщение чата.

        Args:
            chat_id: Чат, в котором пришло сообщение.
            text: Текст сообщения.

        Returns:
            str: Фраза, которую отправляют обратно в тот же чат.
        """
        token = _token_of(text)
        if token is not None:
            return await self._link(chat_id, token)
        user_id = await self._sessions.user_of(chat_id)
        if user_id is None:
            return TELEGRAM_LINK_INSTRUCTION
        if not text.strip():
            return TELEGRAM_EMPTY_COMMAND
        return await self._run(user_id, text)

    async def _link(self, chat_id: int, token: str) -> str:
        """Привязывает чат к аккаунту, названному токеном."""
        user_id = self._links.resolve(token)
        if user_id is None:
            log.info("telegram.link_token_refused", chat_id=chat_id)
            return TELEGRAM_LINK_INSTRUCTION
        await self._sessions.bind(chat_id, user_id)
        log.info("telegram.chat_linked", chat_id=chat_id, user=str(user_id))
        return TELEGRAM_LINKED

    async def _run(self, user_id: UserId, text: str) -> str:
        """Выполняет команду и отвечает на неё фразой того же состава, что и API."""
        try:
            reply = await self._dispatcher.dispatch(user_id, text)
        except (ApplicationError, DomainError) as error:
            _code, message = describe(error)
            return message
        return self._composer.for_result(reply)


def _token_of(text: str) -> str | None:
    """Возвращает код привязки из сообщения вида ``link:<код>``."""
    stripped = text.strip()
    if not stripped.startswith(LINK_PREFIX):
        return None
    return stripped[len(LINK_PREFIX) :].strip() or None
