"""Раздача записанных доменных фактов подписчикам."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class DomainEventDispatcher(Protocol):
    """Отдаёт записанные факты тому, кто на них подписан.

    Раздача происходит после коммита транзакции, поэтому подписчик никогда не
    объявит то, что откатили.
    """

    async def dispatch(self, events: Sequence[object]) -> None:
        """Сообщает факты, записанные с момента последней раздачи."""
