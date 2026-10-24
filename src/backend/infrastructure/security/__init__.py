"""Адаптеры безопасности бэкенда умного дома.

Хеширование паролей и подпись токенов относятся к инфраструктуре: это свойства
конкретного развёртывания и его настройки, а не правила модели. Прикладной слой
видит только два порта из :mod:`backend.application.interfaces.services`, а про
форм JWT, имена алгоритмов и длину ключа знает :mod:`jwt_tokens`.
"""

from backend.infrastructure.security.password_hasher import Pbkdf2PasswordHasher
from backend.infrastructure.security.session_tokens import (
    JwtSessionTokenIssuer,
    MissingSigningSecretError,
)

__all__ = [
    "JwtSessionTokenIssuer",
    "MissingSigningSecretError",
    "Pbkdf2PasswordHasher",
]
