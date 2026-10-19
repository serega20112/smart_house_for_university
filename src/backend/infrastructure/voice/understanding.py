"""Understanding a transcribed sentence on the machine that runs the models.

Speech arrives with far more context than a typed sentence: no punctuation,
numbers that came out of a misheard word and the filler a person uses while
thinking. Rule based parsing cannot recover from that, so the same machine that
recognized the speech is asked for a structured command first.

The HTTP call itself lives in :mod:`backend.infrastructure.nlp.remote`, which is
where the remote understanding pipeline is built; this module only presents it as
the port the voice service declares.
"""

from __future__ import annotations

from backend.application.ports.language import CommandUnderstanding
from backend.application.ports.voice import SpokenCommandUnderstanding
from backend.infrastructure.logging import get_logger
from backend.infrastructure.nlp.remote import (
    RemoteUnderstandingClient,
    RemoteUnderstandingUnavailable,
    understanding_of,
)

log = get_logger("voice.understanding")


class SpokenUnderstandingAdapter(SpokenCommandUnderstanding):
    """Understands a sentence with the remote model.

    Args:
        remote: Client of the machine that runs the models, or None when the
            deployment does not have one.

    Returns:
        None.
    """

    def __init__(self, remote: RemoteUnderstandingClient | None) -> None:
        """Initialize the adapter.

        Args:
            remote: Client of the machine that runs the models, or None when the
                deployment does not have one.

        Returns:
            None.
        """
        self._remote = remote

    async def understand(self, text: str) -> CommandUnderstanding | None:
        """Understand a transcribed sentence.

        Args:
            text: Text produced by the recognizer.

        Returns:
            CommandUnderstanding | None: Structured command, or None when the
            remote model has no answer and the local pipeline has to try.
        """
        if self._remote is None:
            return None
        try:
            answer = await self._remote.ask(text)
        except RemoteUnderstandingUnavailable as unavailable:
            log.info("voice.remote_understanding_unavailable", reason=unavailable.reason)
            return None
        if answer is None or answer.intent is None:
            return None
        return understanding_of(answer)
