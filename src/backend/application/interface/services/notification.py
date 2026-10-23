"""То, что стоит сообщить человеку."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Notification(ABC):
    """Сообщение, которое уходит человеку в выбранный им канал."""

    @property
    @abstractmethod
    def text(self) -> str:
        """Текст, который увидит человек."""

    @property
    @abstractmethod
    def severity(self) -> str:
        """Насколько срочно это сообщение."""
