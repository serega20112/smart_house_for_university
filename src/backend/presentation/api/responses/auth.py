"""Ответы про аккаунт и сессию."""

from __future__ import annotations

from datetime import datetime

from backend.application.dto.views.account_profile import AccountProfile
from backend.application.use_cases.accounts.result import AuthenticatedSession
from backend.presentation.api.responses.common import StrictModel


class UserResponse(StrictModel):
    """Аккаунт таким, каким его видит интерфейс.

    Attributes:
        id: Идентификатор аккаунта.
        email: Логин аккаунта.
        display_name: Имя, показанное в интерфейсе.
        created_at: Момент создания аккаунта.
    """

    id: str
    email: str
    display_name: str
    created_at: datetime


class SessionResponse(StrictModel):
    """Сессия, выданная клиенту.

    Attributes:
        access_token: Токен, который идёт с каждым следующим запросом.
        token_type: Схема, с которой токен передают.
        expires_at: Момент, после которого токен не принимается.
        user: Профиль вошедшего аккаунта.
    """

    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserResponse


class RealtimeTicketResponse(StrictModel):
    """Одноразовый билет, которым интерфейс откроет WebSocket.

    Attributes:
        ticket: Строка билета, годная ровно на один обмен на сессию.
        expires_in_sec: Сколько секунд билет остаётся годным.
    """

    ticket: str
    expires_in_sec: int


def session_of(session: AuthenticatedSession) -> SessionResponse:
    """Возвращает тело сессии.

    Args:
        session: Сессия, которую выдал прикладной слой.

    Returns:
        SessionResponse: Тело сессии.
    """
    return SessionResponse(
        access_token=session.token,
        expires_at=session.expires_at,
        user=profile_of(session.profile),
    )


def profile_of(profile: AccountProfile) -> UserResponse:
    """Возвращает тело профиля аккаунта.

    Args:
        profile: Профиль аккаунта.

    Returns:
        UserResponse: Тело профиля.
    """
    return UserResponse(
        id=str(profile.id),
        email=profile.email,
        display_name=profile.display_name,
        created_at=profile.created_at,
    )
