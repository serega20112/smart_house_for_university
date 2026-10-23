"""Единственное место, которое знает про JWT.

Токенов в системе два — сессия аккаунта и одноразовая привязка чата мессенджера, —
и оба собираются из одних и тех же полей. Держать разбор подписи в каждом из них
значило бы, что смена алгоритма или набора обязательных полей правится в двух
местах, а проверить такой разбор целиком можно только переписав оба.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Final

import jwt
from jwt import InvalidTokenError

from backend.infrastructure.logging import get_logger

log = get_logger("security.jwt_tokens")

ALGORITHM: Final = "HS256"
CLAIM_SUBJECT = "sub"
CLAIM_KIND = "kind"
CLAIM_ISSUED_AT = "iat"
CLAIM_EXPIRES_AT = "exp"
REQUIRED_CLAIMS = (CLAIM_SUBJECT, CLAIM_EXPIRES_AT)


def sign(subject: str, kind: str, secret: str, lifetime: timedelta) -> tuple[str, datetime]:
    """Подписывает токен и возвращает момент, до которого он действует.

    Args:
        subject: Кому токен принадлежит (обычно идентификатор аккаунта).
        kind: Назначение токена: чужой по смыслу токен не должен приниматься.
        secret: Ключ подписи.
        lifetime: Сколько токен живёт.

    Returns:
        tuple[str, datetime]: Токен и момент его истечения.
    """
    issued_at = datetime.now(UTC)
    expires_at = issued_at + lifetime
    token = jwt.encode(
        {
            CLAIM_SUBJECT: subject,
            CLAIM_KIND: kind,
            CLAIM_ISSUED_AT: int(issued_at.timestamp()),
            CLAIM_EXPIRES_AT: int(expires_at.timestamp()),
        },
        secret,
        algorithm=ALGORITHM,
    )
    return token, expires_at


def read(
    token: str,
    secret: str,
    *,
    kind: str,
    leeway_seconds: int = 0,
    refusal_event: str | None = None,
) -> str | None:
    """Возвращает владельца токена или None, если токен не примется.

    Отказ не различается по причине: клиент не должен по ответу понимать, истёк
    токен или был подделан, и ни одна из этих ситуаций не должна рвать запрос.

    Args:
        token: Подписанный токен.
        secret: Ключ подписи.
        kind: Назначение, с которым токен должен был быть выпущен.
        leeway_seconds: Расхождение часов, которое ещё принимается.
        refusal_event: Имя записи в журнале, если отказ нужно заметно отметить.

    Returns:
        str | None: Владелец токена или None.
    """
    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            leeway=leeway_seconds,
            options={"require": list(REQUIRED_CLAIMS)},
        )
    except InvalidTokenError as error:
        if refusal_event is not None:
            log.info(refusal_event, reason=type(error).__name__)
        return None
    if claims.get(CLAIM_KIND) != kind:
        if refusal_event is not None:
            log.info(refusal_event, reason="kind_mismatch")
        return None
    subject = claims.get(CLAIM_SUBJECT)
    return None if subject is None else str(subject)
