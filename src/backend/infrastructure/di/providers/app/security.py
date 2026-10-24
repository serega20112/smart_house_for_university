"""Безопасность: хеш хранящихся паролей и выдача сессий."""

from __future__ import annotations

from dishka import Provider, Scope, provide

from backend.application.interfaces.services.security.password_hasher import PasswordHasher
from backend.application.interfaces.services.security.session_token_issuer import SessionTokenIssuer
from backend.config.settings import Settings
from backend.infrastructure.security.password_hasher import Pbkdf2PasswordHasher
from backend.infrastructure.security.session_tokens import JwtSessionTokenIssuer

APP = Scope.APP


class SecurityProvider(Provider):
    """Криптография, которой аккаунт входит и остаётся в системе."""

    @provide(scope=APP)
    def password_hasher(self, settings: Settings) -> PasswordHasher:
        """Собирает хешер, которым производятся хранящиеся пароли."""
        return Pbkdf2PasswordHasher(
            iterations=settings.pbkdf2_iterations,
            salt_bytes=settings.password_salt_bytes,
        )

    @provide(scope=APP)
    def session_tokens(self, settings: Settings) -> SessionTokenIssuer:
        """Собирает источник токенов сессии."""
        return JwtSessionTokenIssuer(
            secret=settings.auth_token_secret,
            lifetime_minutes=settings.auth_session_lifetime_minutes,
            leeway_seconds=settings.token_leeway_seconds,
        )
