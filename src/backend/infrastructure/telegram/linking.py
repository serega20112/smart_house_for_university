"""Короткие токены, привязывающие чат Telegram к аккаунту.

Бот никогда не видит пароля. Привязка идёт по HTTP: интерфейс просит токен,
отправляет человека с ним к боту, а бот отвечает тем аккаунтом, который токен
называет.

Токен намеренно не токен сессии: сессия живёт днями и разрешает каждый запрос, а
этот живёт минутами и не несёт ничего, кроме названного аккаунта, поэтому
попавший в историю чата или в скриншот токен бесполезен через несколько минут.
"""

from __future__ import annotations

from datetime import timedelta

from backend.application.interface.services.session_token_issuer import SessionTokenIssuer
from backend.domain.exceptions import MalformedIdentifierError
from backend.domain.identifiers import UserId
from backend.infrastructure.logging import get_logger
from backend.infrastructure.security import jwt_tokens
from backend.infrastructure.security.session_tokens import MissingSigningSecretError

log = get_logger("telegram.linking")

LINK_KIND = "telegram_link"
REFUSAL_EVENT = "telegram.link_token_refused"


class TelegramLinkTokenIssuer:
    """Выдаёт и разбирает одноразовые токены привязки бота.

    Args:
        sessions: Выдающий сессии адаптер, чей ключ и настройку токены привязки
            разделяют, чтобы у развёртывания был один ключ.
        lifetime_minutes: Сколько токен привязки остаётся годным.
    """

    def __init__(self, sessions: SessionTokenIssuer, lifetime_minutes: int) -> None:
        """Инициализирует адаптер привязки.

        Args:
            sessions: Выдающий сессии адаптер.
            lifetime_minutes: Сколько токен привязки остаётся годным.
        """
        self._sessions = sessions
        self._lifetime = timedelta(minutes=lifetime_minutes)

    def issue(self, user_id: UserId) -> str:
        """Создаёт одноразовый токен, связывающий чат с аккаунтом.

        Args:
            user_id: Аккаунт, к которому чат привязывают.

        Returns:
            str: Подписанный токен, который отправляют боту.
        """
        token, _expires_at = jwt_tokens.sign(
            str(user_id), LINK_KIND, _secret_of(self._sessions), self._lifetime
        )
        return token

    def resolve(self, token: str) -> UserId | None:
        """Возвращает аккаунт, названный токеном привязки.

        Args:
            token: Токен, который человек прислал боту.

        Returns:
            UserId | None: Привязанный аккаунт либо None, если токен не годится.
        """
        subject = jwt_tokens.read(
            token,
            _secret_of(self._sessions),
            kind=LINK_KIND,
            refusal_event=REFUSAL_EVENT,
        )
        if subject is None:
            return None
        try:
            return UserId.parse(subject)
        except MalformedIdentifierError:
            log.info(REFUSAL_EVENT, reason="subject_is_not_an_identifier")
            return None


def _secret_of(sessions: SessionTokenIssuer) -> str:
    """Возвращает ключ подписи адаптера, выдающего сессии.

    Args:
        sessions: Выдающий сессии адаптер.

    Returns:
        str: Общий ключ подписи.

    Raises:
        MissingSigningSecretError: Когда адаптер ключа не открывает, то есть
            развёртывание подвязало что-то другое вместо JWT-выдающего.
    """
    secret = getattr(sessions, "secret", None)
    if not isinstance(secret, str) or not secret:
        raise MissingSigningSecretError(
            "the session token issuer does not expose its signing secret"
        )
    return secret
