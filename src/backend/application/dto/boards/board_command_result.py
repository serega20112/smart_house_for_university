"""Ответ платы на команду реле или смену сети."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BoardCommandResult:
    """Что плата ответила на команду.

    Attributes:
        accepted: Подтвердила ли плата команду.
        reason: Машинная причина отказа или None при успехе.
    """

    accepted: bool
    reason: str | None = None

    @property
    def outcome(self) -> str:
        """Возвращает меточную надпись итога для счётчика наблюдаемости.

        Returns:
            str: `accepted` для подтверждённой команды или машинная причина отказа.
        """
        if self.accepted:
            return "accepted"
        return self.reason or "rejected"
