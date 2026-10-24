"""Имена ключей и каналов Redis всего адаптера.

Префикс отделения отделяет одно развёртывание от другого, когда они делят один
сервер; всё остальное — сегменты, собранные здесь в одном месте, чтобы издатель
событий, подписчик, хранилище состояний и аренда не строили одно и то же имя
каждый по-своему.
"""

from __future__ import annotations

from backend.domain.identifiers import UserId

STATE_SEGMENT = "state"
OVERRIDE_SEGMENT = "override_until"
THROTTLE_SEGMENT = "throttle"
CHAT_SEGMENT = "chat"
USER_SEGMENT = "user"
LOCK_SEGMENT = "lock"
GLOBAL_CHANNEL = "all"


def state_key(prefix: str, user_id: UserId) -> str:
    """Возвращает имя хеша с живым состоянием дома."""
    return f"{prefix}:{STATE_SEGMENT}:{user_id}"


def override_key(prefix: str, user_id: UserId) -> str:
    """Возвращает имя ключа окна ручного управления."""
    return f"{prefix}:{OVERRIDE_SEGMENT}:{user_id}"


def throttle_key(prefix: str, user_id: UserId, name: str) -> str:
    """Возвращает имя ключа, занимаемого под одно периодическое уведомление."""
    return f"{prefix}:{THROTTLE_SEGMENT}:{user_id}:{name}"


def chat_key(prefix: str, chat_id: int) -> str:
    """Возвращает имя ключа «чат — аккаунт»."""
    return f"{prefix}:{CHAT_SEGMENT}:{chat_id}"


def user_key(prefix: str, user_id: UserId) -> str:
    """Возвращает имя ключа «аккаунт — чат»."""
    return f"{prefix}:{USER_SEGMENT}:{user_id}"


def lock_key(prefix: str, name: str) -> str:
    """Возвращает имя ключа аренды."""
    return f"{prefix}:{LOCK_SEGMENT}:{name}"


def user_channel(prefix: str, user_id: UserId) -> str:
    """Возвращает имя канала одного аккаунта."""
    return f"{prefix}:{USER_SEGMENT}:{user_id}"


def global_channel(prefix: str) -> str:
    """Возвращает имя канала, обращённого ко всем."""
    return f"{prefix}:{USER_SEGMENT}:{GLOBAL_CHANNEL}"
