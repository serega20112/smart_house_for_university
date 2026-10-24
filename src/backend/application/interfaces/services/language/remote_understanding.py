"""Клиент машины, крутящей модели понимания фраз."""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.application.dto.language.remote_answer import RemoteAnswer


class RemoteUnderstanding(ABC):
    """Спрашивает у модели, что значит предложение."""

    @abstractmethod
    async def ask(self, text: str) -> RemoteAnswer | None:
        """Просит удалённую модель понять предложение.

        Args:
            text: Предложение таким, каким его получил интерфейс.

        Returns:
            RemoteAnswer | None: Структурированная команда, или None, когда
            предложение вообще ни о какой команде не говорит.

        Raises:
            RemoteUnderstandingUnavailable: Когда удалённая модель не может ответить.
        """
