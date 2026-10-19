"""Wording of the voice channel answers.

The application layer never writes user facing text, so the pipeline asks a
composer for the phrase it should speak. The very same strings are shown in the
interface and sent to Telegram, which keeps a spoken answer and a typed one from
drifting apart.
"""

from __future__ import annotations

from backend.application.dto.command import CommandResult
from backend.application.interface.services import ReplyComposer
from backend.presentation.api.messages import (
    command_message,
    voice_no_speech_message,
    voice_unavailable_message,
)


class CommandReplyComposer(ReplyComposer):
    """Turns a command result into the phrase the user hears."""

    def compose(self, result: object) -> str:
        """Return what to say after a command was executed.

        Args:
            result: Structured result of the command.

        Returns:
            str: Phrase for the user.
        """
        if isinstance(result, CommandResult):
            return command_message(result)
        return voice_unavailable_message()

    def compose_no_speech(self) -> str:
        """Return what to say when nothing was recognized.

        Returns:
            str: Phrase for the user.
        """
        return voice_no_speech_message()

    def compose_unavailable(self) -> str:
        """Return what to say when the voice service is down.

        Returns:
            str: Phrase for the user.
        """
        return voice_unavailable_message()