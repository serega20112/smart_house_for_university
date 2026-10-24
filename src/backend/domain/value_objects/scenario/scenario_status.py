"""Этап жизни отложенного сценария."""

from __future__ import annotations

from enum import StrEnum


class ScenarioStatus(StrEnum):
    """Где сценарий находится в своей жизни."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    @property
    def is_final(self) -> bool:
        """Сообщает, будет ли сценарий действовать ещё когда-нибудь.

        Returns:
            bool: True для завершённых, проваленных и отменённых сценариев.
        """
        return self in _FINAL_STATUSES

    @property
    def holds_control_priority(self) -> bool:
        """Сообщает, ставит ли сценарий себя выше автоматики.

        Returns:
            bool: True для ожидающих и идущих сценариев.
        """
        return self in (ScenarioStatus.PENDING, ScenarioStatus.RUNNING)


_FINAL_STATUSES: frozenset[ScenarioStatus] = frozenset(
    {
        ScenarioStatus.COMPLETED,
        ScenarioStatus.FAILED,
        ScenarioStatus.CANCELLED,
    }
)
