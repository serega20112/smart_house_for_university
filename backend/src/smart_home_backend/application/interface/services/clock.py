"""Clock port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime


class Clock(ABC):
    """Source of the current time."""

    @abstractmethod
    def now(self) -> datetime:
        """Return the current moment in UTC.

        Returns:
            datetime: Current moment.
        """
