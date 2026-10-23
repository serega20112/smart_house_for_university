"""Токены сессии, подписанные PyJWT.

Токен — обычный JWT на HS256. Нигде он не хранится, поэтому потеря ключа подписи
разлогинивает всех: именно это ждёт свежее развёртывание и именно это должно
случиться при ротации утечки.

Ключ не придумывается в момент запуска: конфигурация без ключа отвергается до
того, как процесс обслужит первый запрос.
"""

from __future__ import annotations

from datetime import timedelta

from backend.application.dto.account.issued_session import IssuedSession
from backend.application.interface.services.session_token_issuer import SessionTokenIssuer
from backend.domain.exceptions import MalformedIdentifierError
from backend.domain.identifiers import UserId
from backend.infrastructure.security import jwt_tokens

TOKEN_KIND = "session"
MINIMUM_SECRET_LENGTH = 32


class MissingSigningSecretError(RuntimeError):
    """Ключа подписи нет, либо он короче, чем можно подписывать.

    Args:
        message: Причина человеческими словами.
    """

    def __init__(self, message: str | None = None) -> None:
        """Инициализирует отказ.

        Args:
            message: Причина человеческими словами, если вызывающий знает её точнее.

        Returns:
            None.
        """
        super().__init__(
            message
            or f"AUTH_TOKEN_SECRET must be set and be at least {MINIMUM_SECRET_LENGTH} characters"
        )


class JwtSessionTokenIssuer(SessionTokenIssuer):
    """Выдаёт и разбирает токены сессии на HS256.

    Args:
        secret: Ключ подписи.
        lifetime_minutes: Срок только что выданной сессии.
        leeway_seconds: Расхождение часов, которое ещё принимается при проверке.

    Raises:
        MissingSigningSecretError: Когда ключа нет или он короче допустимого.
    """

    def __init__(self, secret: str, lifetime_minutes: int, leeway_seconds: int = 0) -> None:
        """Инициализирует адаптер, выдающий токены.

        Args:
            secret: Ключ подписи.
            lifetime_minutes: Срок только что выданной сессии.
            leeway_seconds: Расхождение часов, которое ещё принимается при проверке.

        Returns:
            None.

        Raises:
            MissingSigningSecretError: Когда ключа нет или он короче допустимого.
        """
        if len(secret) < MINIMUM_SECRET_LENGTH:
            raise MissingSigningSecretError()
        self._secret = secret
        self._lifetime = timedelta(minutes=lifetime_minutes)
        self._leeway = leeway_seconds

    @property
    def secret(self) -> str:
        """Возвращает ключ подписи.

        Адаптеры, подписывающие что-то уже, чем сессия, — например одноразовый
        токен привязки чата мессенджера, — берут этот ключ здесь, а не просят у
        развёртывания второй ключ, который потом пришлось бы менять дважды.

        Returns:
            str: Ключ подписи.
        """
        return self._secret

    def issue(self, user_id: UserId) -> IssuedSession:
        """Создаёт новую сессию аккаунта.

        Args:
            user_id: Аккаунт, которому сессия принадлежит.

        Returns:
            IssuedSession: Токен и момент его истечения.
        """
        token, expires_at = jwt_tokens.sign(str(user_id), TOKEN_KIND, self._secret, self._lifetime)
        return IssuedSession(token=token, expires_at=expires_at)

    def resolve(self, token: str) -> UserId | None:
        """Возвращает аккаунт, для которого токен был выдан.

        Любой отказ отвечает None: клиент не должен по ответу различать истёкший
        токен и подделанный, и ни тот, ни другой не должен рвать запрос исключением.

        Args:
            token: Токен, который принёс клиент.

        Returns:
            UserId | None: Владелец токена, либо None когда токен не годится.
        """
        subject = jwt_tokens.read(
            token,
            self._secret,
            kind=TOKEN_KIND,
            leeway_seconds=self._leeway,
        )
        if subject is None:
            return None
        try:
            return UserId.parse(subject)
        except MalformedIdentifierError:
            return None
