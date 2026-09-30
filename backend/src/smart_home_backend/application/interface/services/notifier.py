"""User notification port."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Notifier(ABC):
    """Delivery channel for notifications about significant events."""

    @abstractmethod
    async def notify(self, text: str) -> None:
        """Send a notification to the user.

        Args:
            text: Notification text.

        Returns:
            None.
        """
