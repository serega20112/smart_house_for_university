"""Ответы про настройку автоматизации."""

from __future__ import annotations

from backend.domain.value_objects.automation.automation_view import AutomationView
from backend.presentation.api.responses.common import StrictModel


class AutomationResponse(StrictModel):
    """Настройка автоматизации такой, какой её видит интерфейс.

    Attributes:
        enabled: Работает ли автоматизация.
        target_temperature: Температуру, которую дому велят держать.
        target_humidity: Влажность, которую дому велят держать.
        temperature_tolerance: Насколько температуре позволено уйти.
        humidity_tolerance: Насколько позволено уйти влажности.
        participating_device_ids: Устройства, которыми автоматизации разрешено управлять.
    """

    enabled: bool
    target_temperature: float
    target_humidity: float
    temperature_tolerance: float
    humidity_tolerance: float
    participating_device_ids: list[str]


def automation_of(automation: AutomationView) -> AutomationResponse:
    """Возвращает тело настройки автоматизации.

    Args:
        automation: Настройка таким, каким её видит прикладной слой.

    Returns:
        AutomationResponse: Тело настройки.
    """
    return AutomationResponse(
        enabled=automation.enabled,
        target_temperature=automation.target_temperature,
        target_humidity=automation.target_humidity,
        temperature_tolerance=automation.temperature_tolerance,
        humidity_tolerance=automation.humidity_tolerance,
        participating_device_ids=sorted(str(item) for item in automation.participating_device_ids),
    )
