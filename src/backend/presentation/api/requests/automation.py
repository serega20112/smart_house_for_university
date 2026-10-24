"""Тело запроса автоматизации и перевод его в частичное изменение настройки."""

from __future__ import annotations

from pydantic import Field

from backend.application.dto.automation.automation_patch import AutomationPatch
from backend.domain.identifiers import DeviceId
from backend.domain.value_objects.climate.humidity import Humidity
from backend.domain.value_objects.climate.temperature import Temperature
from backend.presentation.api.base import StrictModel

TEMPERATURE_MIN = -50.0
TEMPERATURE_MAX = 80.0
TEMPERATURE_TOLERANCE_MAX = 20.0
HUMIDITY_MIN = 0.0
HUMIDITY_MAX = 100.0
HUMIDITY_TOLERANCE_MAX = 50.0


class AutomationUpdateBody(StrictModel):
    """Частичное изменение настройки автоматизации.

    Attributes:
        enabled: Новый признак работы или None.
        target_temperature: Новая целевая температура или None.
        temperature_tolerance: Новый допуск температуры или None.
        target_humidity: Новая целевая влажность или None.
        humidity_tolerance: Новый допуск влажности или None.
        participating_device_ids: Новые участники или None.
    """

    enabled: bool | None = None
    target_temperature: float | None = Field(default=None, ge=TEMPERATURE_MIN, le=TEMPERATURE_MAX)
    temperature_tolerance: float | None = Field(default=None, ge=0.0, le=TEMPERATURE_TOLERANCE_MAX)
    target_humidity: float | None = Field(default=None, ge=HUMIDITY_MIN, le=HUMIDITY_MAX)
    humidity_tolerance: float | None = Field(default=None, ge=0.0, le=HUMIDITY_TOLERANCE_MAX)
    participating_device_ids: list[str] | None = None


def patch_of(body: AutomationUpdateBody) -> AutomationPatch:
    """Возвращает команду частичного изменения настройки.

    Args:
        body: Поля, которые нужно изменить.

    Returns:
        AutomationPatch: Команда, понятная сценарию приложения.
    """
    return AutomationPatch(
        enabled=body.enabled,
        target_temperature=(
            None if body.target_temperature is None else Temperature(body.target_temperature)
        ),
        temperature_tolerance=body.temperature_tolerance,
        target_humidity=(None if body.target_humidity is None else Humidity(body.target_humidity)),
        humidity_tolerance=body.humidity_tolerance,
        participating_device_ids=(
            None
            if body.participating_device_ids is None
            else frozenset(DeviceId.parse(item) for item in body.participating_device_ids)
        ),
    )
