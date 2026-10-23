"""Выдача и разбор токенов сессии."""

from __future__ import annotations

from abc import ABC, abstractmethod

from backend.application.dto.account.issued_session import IssuedSession
from backend.domain.identifiers import UserId


class SessionTokenIssuer(ABC):
    """Выпускает токены сессии и узнаёт аккаунт по токену."""

    @abstractmethod
    def issue(self, user_id: UserId) -> IssuedSession:
        """Открывает сессию аккаунта."""

    @abstractmethod
    def resolve(self, token: str) -> UserId | None:
        """Аккаунт выдавшего токен или None, если токен не годится."""
