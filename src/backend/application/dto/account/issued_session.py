"""Сессия, выданная клиенту."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class IssuedSession:
    """Токен сессии и момент его конца.

    Attributes:
        token: Подписанный токен.
        expires_at: Момент, после которого токен не принимается.
    """

    token: str
    expires_at: datetime
