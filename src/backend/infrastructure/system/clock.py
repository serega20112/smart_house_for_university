"""Адаптер системных часов.

Модель часы не читает, поэтому каждая метка времени в системе приходит из этого
единственного адаптера. Тест заменяет его своей реализацией
:class:`~backend.application.interfaces.services.system.clock.Clock`, а не замораживает
время на весь процесс.
"""

from __future__ import annotations

from datetime import UTC, datetime

from backend.application.interfaces.services.system.clock import Clock


class SystemClock(Clock):
    """Часы, читающие системное время в UTC."""

    def now(self) -> datetime:
        """Возвращает текущий момент в UTC."""
        return datetime.now(UTC)
