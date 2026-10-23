"""Результаты сценариев аккаунтов."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from backend.domain.value_objects.account.account_profile import AccountProfile


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    """Вошедший аккаунт и открывшаяся для него сессия.

    Attributes:
        profile: Профиль вошедшего аккаунта.
        token: Токен сессии, который носил каждый следующий запрос.
        expires_at: Момент, после которого токен не принимается.
    """

    profile: AccountProfile
    token: str
    expires_at: datetime
