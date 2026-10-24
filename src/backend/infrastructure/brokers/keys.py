"""Имена ключей и каналов Redis всего адаптера.

Префикс отделения отделяет одно развёртывание от другого, когда они делят один
сервер; всё остальное — сегменты, собранные здесь в одном месте, чтобы издатель
событий, подписчик, хранилище состояний и аренда не строили одно и то же имя
каждый по-своему.
"""

from __future__ import annotations

from backend.domain.identifiers import EspDeviceId, UserId

STATE_SEGMENT = "state"
OVERRIDE_SEGMENT = "override_until"
THROTTLE_SEGMENT = "throttle"
CHAT_SEGMENT = "chat"
USER_SEGMENT = "user"
LOCK_SEGMENT = "lock"
GLOBAL_CHANNEL = "all"
BOARD_SEGMENT = "board"
ONLINE_SEGMENT = "online"
COMMAND_SEGMENT = "command"
RESULT_SEGMENT = "result"
REALTIME_TICKET_SEGMENT = "realtime_ticket"


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


def board_presence_key(prefix: str, user_id: UserId, board_id: EspDeviceId) -> str:
    """Возвращает имя ключа присутствия одной подключённой платы."""
    return f"{prefix}:{BOARD_SEGMENT}:{ONLINE_SEGMENT}:{user_id}:{board_id}"


def board_presence_pattern(prefix: str, user_id: UserId) -> str:
    """Возвращает шаблон ключей присутствия всех плат одного аккаунта."""
    return f"{prefix}:{BOARD_SEGMENT}:{ONLINE_SEGMENT}:{user_id}:*"


def board_presence_all_pattern(prefix: str) -> str:
    """Возвращает шаблон ключей присутствия плат всех аккаунтов."""
    return f"{prefix}:{BOARD_SEGMENT}:{ONLINE_SEGMENT}:*"


def board_command_channel(prefix: str, user_id: UserId) -> str:
    """Возвращает канал команд, адресованных платам одного аккаунта."""
    return f"{prefix}:{BOARD_SEGMENT}:{COMMAND_SEGMENT}:{user_id}"


def board_command_pattern(prefix: str) -> str:
    """Возвращает шаблон каналов команд всех аккаунтов."""
    return f"{prefix}:{BOARD_SEGMENT}:{COMMAND_SEGMENT}:*"


def board_result_channel(prefix: str, command_id: str) -> str:
    """Возвращает канал ответа на одну команду платы."""
    return f"{prefix}:{BOARD_SEGMENT}:{RESULT_SEGMENT}:{command_id}"


def realtime_ticket_key(prefix: str, ticket: str) -> str:
    """Возвращает имя одноразового билета, которым WebSocket меняется на сессию."""
    return f"{prefix}:{REALTIME_TICKET_SEGMENT}:{ticket}"
