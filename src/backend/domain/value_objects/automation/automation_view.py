"""Настройки климата в том виде, в каком их показывает экран."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.identifiers import DeviceId


@dataclass(frozen=True, slots=True)
class AutomationView:
    """Состояние климатической автоматизации для интерфейса.

    Attributes:
        enabled: Активна ли автоматизация.
        target_temperature: Температура, которую дом должен держать.
        target_humidity: Влажность, которую дом должен держать.
        temperature_tolerance: Допустимое отклонение температуры.
        humidity_tolerance: Допустимое отклонение влажности.
        participating_device_ids: Устройства, которыми автоматизация вправе управлять.
    """

    enabled: bool
    target_temperature: float
    target_humidity: float
    temperature_tolerance: float
    humidity_tolerance: float
    participating_device_ids: frozenset[DeviceId]
