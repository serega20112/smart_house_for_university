"""Отказы, которые относятся к прикладному слою.

Домен объявляет то, что отвергает модель; этот модуль объявляет то, что отвергает
приложение, познакомившись с внешним миром. Логин, не совпавший с сохранённым хешем, —
не неизменяемое условие агрегата, как и повторный логин, и устройство, которое
хранилище не нашло, поэтому ничто из этого домену не принадлежит.

Презентация один раз ставит каждый тип этого модуля против HTTP-статуса в одной таблице
обработчиков. Больше никто в системе не должен знать ни одного кода ответа.
"""

from __future__ import annotations

from typing import Any

from backend.application.dto.language.clarification_reason import ClarificationReason
from backend.domain.identifiers import DeviceId, EspDeviceId, ScenarioId, UserId

__all__ = [
    "AccountNotFoundError",
    "ApplicationError",
    "BoardAlreadyClaimedError",
    "BoardNotFoundError",
    "BoardUnreachableError",
    "ClaimNotFoundError",
    "CommandNotUnderstoodError",
    "ConcurrentModificationError",
    "DeviceNotFoundError",
    "EmailAlreadyTakenError",
    "InvalidCredentialsError",
    "NoDeviceForCapabilityError",
    "ScenarioNotFoundError",
]


class ApplicationError(Exception):
    """Общий класс каждого отказа, порождённого прикладным слоем."""


class InvalidCredentialsError(ApplicationError):
    """Логин не совпадает с сохранённым аккаунтом.

    Одна и та же ошибка отвечает и на неизвестный логин, и на неверный пароль, чтобы
    ответ никогда не выдавал, существует ли аккаунт.
    """

    def __init__(self) -> None:
        super().__init__("login or password is wrong")


class EmailAlreadyTakenError(ApplicationError):
    """Запрошенный логин уже использует другой аккаунт.

    Args:
        email: Запрошенный логин.
    """

    def __init__(self, email: str) -> None:
        super().__init__(f"email {email} is already registered")
        self.email = email


class AccountNotFoundError(ApplicationError):
    """Ни один аккаунт не совпал с запрошенным идентификатором.

    Args:
        user_id: Идентификатор, который не удалось разрешить.
    """

    def __init__(self, user_id: UserId) -> None:
        super().__init__(f"account {user_id} does not exist")
        self.user_id = user_id


class DeviceNotFoundError(ApplicationError):
    """У аккаунта нет устройства с таким идентификатором.

    Args:
        device_id: Идентификатор, который не удалось разрешить.
    """

    def __init__(self, device_id: DeviceId) -> None:
        super().__init__(f"device {device_id} does not exist")
        self.device_id = device_id


class ScenarioNotFoundError(ApplicationError):
    """У аккаунта нет сценария с таким идентификатором.

    Args:
        scenario_id: Идентификатор, который не удалось разрешить.
    """

    def __init__(self, scenario_id: ScenarioId) -> None:
        super().__init__(f"scenario {scenario_id} does not exist")
        self.scenario_id = scenario_id


class BoardNotFoundError(ApplicationError):
    """У аккаунта нет платы с таким идентификатором.

    Args:
        board_id: Идентификатор, который не удалось разрешить.
    """

    def __init__(self, board_id: EspDeviceId) -> None:
        super().__init__(f"board {board_id} does not exist")
        self.board_id = board_id


class ClaimNotFoundError(ApplicationError):
    """Ни одно открытое предложение не несёт предъявленный токен.

    Args:
        token: Идентификатор, который не удалось разрешить.
    """

    def __init__(self, token: str) -> None:
        super().__init__(f"no announced board carries the token {token}")
        self.token = token


class BoardUnreachableError(ApplicationError):
    """Плата за устройством не ответила.

    Args:
        reason: Машинночитаемая причина, которую сообщил транспорт.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(f"the board did not accept the command: {reason}")
        self.reason = reason


class ConcurrentModificationError(ApplicationError):
    """Другой записывающий изменил агрегат под этим.

    Тот, кто прочитал старую ревизию строки, не вправе решать, как строка выглядит
    сейчас: хранилище отвергает его устаревшую запись. От вызывающего ждут, что он
    перечитает свежий снимок и повторит намерение, а не перетрёт изменение, которого
    не видел.

    Args:
        aggregate: Человекочитаемое имя агрегата.
        aggregate_id: Идентификатор агрегата, который ушёл вперёд.
    """

    def __init__(self, aggregate: str, aggregate_id: object) -> None:
        super().__init__(f"{aggregate} {aggregate_id} changed under this writer")
        self.aggregate = aggregate
        self.aggregate_id = aggregate_id


class NoDeviceForCapabilityError(ApplicationError):
    """Ни одно устройство дома не умеет запрошенное.

    Это решение приложения, а не инвариант модели: каждое устройство по
    отдельности вполне может быть исправным, просто в доме нет такого, которое
    умеет запрошенное.

    Attributes:
        capability: Запрошенная способность.
    """

    def __init__(self, capability: str) -> None:
        super().__init__(f"no device in this home supports {capability}")
        self.capability = capability


class BoardAlreadyClaimedError(ApplicationError):
    """Плату раньше забрал другой аккаунт.

    Предложение ещё открыто в памяти агрегата, но хранилище отвечает, что гонку
    выиграл кто-то другой, и это знает только граница транзакции.
    """

    def __init__(self) -> None:
        super().__init__("this board is already owned by another account")


class CommandNotUnderstoodError(ApplicationError):
    """Написанную свободную команду нельзя выполнить как она есть.

    Args:
        reason: Почему команду нельзя выполнить.
        details: Что человеку надо добавить или изменить.
    """

    def __init__(self, reason: ClarificationReason, **details: Any) -> None:
        super().__init__(f"command needs clarification: {reason.value}")
        self.reason = reason
        self.details = details
