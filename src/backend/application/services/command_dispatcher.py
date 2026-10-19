"""Command bus: one handler per intent, no god object.

The bus is the only place that knows which handler serves which intent. Adding a
new thing a person may say means adding one handler and one line in the registry; it
never means editing a class that already knows about every other action in the
system.

Handlers receive the owner and what was understood, and they talk to services rather
than to other handlers. That is what keeps the boundary between two use cases from
dissolving into a chain of calls with no transaction in sight.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from backend.application.dto.home import CommandReply
from backend.application.errors import CommandNotUnderstoodError
from backend.application.ports.language import (
    ClarificationReason,
    CommandUnderstanding,
    CommandUnderstandingPort,
    Intent,
)
from backend.application.ports.voice import ReplyComposer
from backend.domain.identifiers import UserId

CommandHandler = Callable[[UserId, CommandUnderstanding], Awaitable[CommandReply]]


class CommandDispatcher:
    """Understands a free form sentence and routes it to the right handler."""

    def __init__(
        self,
        understanding: CommandUnderstandingPort,
        handlers: dict[Intent, CommandHandler],
        composer: ReplyComposer,
    ) -> None:
        """Initialize the dispatcher.

        Args:
            understanding: Pipeline turning a sentence into a structured command.
            handlers: Handler of every intent that can be carried out.
            composer: Builds the wording of the answers.

        Returns:
            None.
        """
        self._understanding = understanding
        self._handlers = handlers
        self._composer = composer

    async def dispatch(self, user_id: UserId, text: str) -> CommandReply:
        """Understand a sentence and carry out what it asks for.

        Args:
            user_id: Owner the command is executed for.
            text: Sentence as typed or as transcribed.

        Returns:
            CommandReply: What carrying the command out produced.

        Raises:
            CommandNotUnderstoodError: When the sentence cannot be carried out as it
            stands. The reason travels with the exception so the interface can ask the
            right follow up question.
        """
        parsed = await self._understanding.understand(text)
        if parsed.intent is None:
            raise CommandNotUnderstoodError(ClarificationReason.UNRECOGNIZED_INTENT)
        if not await self._understanding.is_confident_enough(parsed):
            raise CommandNotUnderstoodError(
                ClarificationReason.LOW_CONFIDENCE, confidence=parsed.confidence
            )
        handler = self._handlers.get(parsed.intent)
        if handler is None:
            raise CommandNotUnderstoodError(ClarificationReason.UNRECOGNIZED_INTENT)
        return await handler(user_id, parsed)

    def compose(self, result: CommandReply) -> str:
        """Return the phrase describing what a command produced.

        Args:
            result: Result of a dispatched command.

        Returns:
            str: Phrase for the user.
        """
        return result.answer or self._composer.for_result(result)
