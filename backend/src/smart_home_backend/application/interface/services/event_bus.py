"""Realtime event publication port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class EventBus(ABC):
    """Publisher of domain events to any number of subscribers."""

    @abstractmethod
    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """Broadcast an event to all subscribers.

        Args:
            event_type: Event name such as device.state_changed.
            payload: JSON serializable event data.

        Returns:
            None.
        """
