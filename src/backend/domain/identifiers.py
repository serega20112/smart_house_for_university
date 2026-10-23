"""Типизированные идентификаторы агрегатов.

Идентичность принадлежит домену: суррогатный целочисленный ключ, который выдаёт
база, — не тот идентификатор, про который модель может рассуждать, поэтому
агрегат создаётся уже с идентификатором, и хранилище никогда не назначает его
постфактум.

У каждого агрегата свой тип, поэтому передать идентификатор сценария туда, где
ждут идентификатор устройства, не получится, а слой хранения пишет ровно тот же
UUID, ничего не перекодируя.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self
from uuid import UUID, uuid4

from backend.domain.exceptions import MalformedIdentifierError


@dataclass(frozen=True, slots=True)
class UuidIdentifier:
    """Общее поведение любого идентификатора модели.

    Наследники остаются разными типами для проверщика типов, получая правила
    создания и разбора по наследованию, — поэтому правила написаны один раз.

    Attributes:
        value: UUID, стоящий за идентификатором.
    """

    value: UUID

    def __post_init__(self) -> None:
        """Проверяет, что внутри настоящий UUID.

        Raises:
            MalformedIdentifierError: Когда значение не является UUID.
        """
        if not isinstance(self.value, UUID):
            raise MalformedIdentifierError(type(self).__name__, self.value)

    @classmethod
    def generate(cls) -> Self:
        """Создаёт идентификатор, которого раньше не было.

        Returns:
            Self: Новый идентификатор.
        """
        return cls(uuid4())

    @classmethod
    def parse(cls, raw: str | UUID) -> Self:
        """Восстанавливает идентификатор из хранимого или переданного вида.

        Args:
            raw: UUID текстом или уже разобранным UUID.

        Returns:
            Self: Разобранный идентификатор.

        Raises:
            MalformedIdentifierError: Когда текст не является UUID.
        """
        if isinstance(raw, UUID):
            return cls(raw)
        try:
            return cls(UUID(str(raw)))
        except (TypeError, ValueError) as error:
            raise MalformedIdentifierError(cls.__name__, raw) from error

    def __str__(self) -> str:
        """Канонический текстовый вид: UUID строчными буквами с дефисами."""
        return str(self.value)


@dataclass(frozen=True, slots=True)
class UserId(UuidIdentifier):
    """Идентификатор аккаунта."""


@dataclass(frozen=True, slots=True)
class DeviceId(UuidIdentifier):
    """Идентификатор логического устройства."""


@dataclass(frozen=True, slots=True)
class ScenarioId(UuidIdentifier):
    """Идентификатор временного сценария."""


@dataclass(frozen=True, slots=True)
class EspDeviceId(UuidIdentifier):
    """Идентификатор сопряжённой платы."""


@dataclass(frozen=True, slots=True)
class EspClaimId(UuidIdentifier):
    """Идентификатор объявления платы, которая ждёт владельца."""
