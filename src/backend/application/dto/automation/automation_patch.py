"""Частичное изменение настройки автоматизации."""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.identifiers import DeviceId
from backend.domain.value_objects.climate.humidity import Humidity
from backend.domain.value_objects.climate.temperature import Temperature


@dataclass(frozen=True, slots=True)
class AutomationPatch:
    """Поля настройки автоматизации, которые человек хочет изменить.

    Каждое поле необязательное, а None означает «оставить»: благодаря этому один
    сценарий приложения обслуживает всю настройку вместо семейства почти одинаковых,
    различающихся одним числом.

    Attributes:
        enabled: Новый признак работы или None.
        target_temperature: Новая целевая температура или None.
        temperature_tolerance: Новый допуск температуры или None.
        target_humidity: Новая целевая влажность или None.
        humidity_tolerance: Новый допуск влажности или None.
        participating_device_ids: Новые участники или None.
    """

    enabled: bool | None = None
    target_temperature: Temperature | None = None
    temperature_tolerance: float | None = None
    target_humidity: Humidity | None = None
    humidity_tolerance: float | None = None
    participating_device_ids: frozenset[DeviceId] | None = None
