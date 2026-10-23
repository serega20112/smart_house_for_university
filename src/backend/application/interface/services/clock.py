"""Источник текущего момента."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime


class Clock(ABC):
    """Отдаёт текущее время."""

    @abstractmethod
    def now(self) -> datetime:
        """Текущий момент в UTC."""
