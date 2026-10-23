"""Что конвейер понял из свободной формулировки."""

from __future__ import annotations

from dataclasses import dataclass

from backend.application.dto.language.intent import Intent
from backend.domain.value_objects.climate.temperature import Temperature
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind


@dataclass(frozen=True, slots=True)
class CommandUnderstanding:
    """Разобранное предложение: намерение и названные параметры.

    Attributes:
        intent: Распознанное намерение или None, если не распознано ничего.
        device_name: Фрагмент имени устройства из предложения.
        device_kinds: Виды устройств, о которых могло идти речь.
        capability: Способность, если человек её назвал.
        temperature: Запрошенная температура.
        humidity: Запрошенная влажность.
        delay_minutes: Запрошенная задержка запуска сценария.
        target: Место или предмет, который назвал человек.
        confidence: Уверенность конвейера от нуля до единицы.
    """

    intent: Intent | None = None
    device_name: str | None = None
    device_kinds: frozenset[DeviceKind] = frozenset()
    capability: Capability | None = None
    temperature: Temperature | None = None
    humidity: float | None = None
    delay_minutes: int | None = None
    target: str | None = None
    confidence: float = 0.0

    @property
    def carries_home_reference(self) -> bool:
        """Назвал ли человек то, о чём он говорит."""
        return bool(self.device_name or self.device_kinds)
