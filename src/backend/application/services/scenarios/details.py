"""Мелочи, общие для шага сценария и его сворачивания."""

from __future__ import annotations

from backend.application.errors import (
    BoardUnreachableError,
    NoDeviceForCapabilityError,
)
from backend.domain.aggregates.scenario.scenario import Scenario
from backend.domain.identifiers import DeviceId
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.domain.value_objects.scenario.finish_reason import FinishReason
from backend.domain.value_objects.scenario.scenario_view import ScenarioView

EXPECTED_REFUSALS: tuple[type[Exception], ...] = (
    NoDeviceForCapabilityError,
    BoardUnreachableError,
)


def reason_of(refusal: Exception) -> FinishReason:
    """Какая запись словаря причин соответствует ожидаемому отказу.

    Args:
        refusal: Отказ, из-за которого сценарий умер.

    Returns:
        FinishReason: Причина, которая попадёт на сценарий.
    """
    if isinstance(refusal, BoardUnreachableError):
        return FinishReason.BOARD_UNREACHABLE
    return FinishReason.NO_DEVICE_FOR_CAPABILITY


def restorable_states(captured: dict[DeviceId, DeviceStatus]) -> dict[DeviceId, DeviceStatus]:
    """Оставляет только те состояния, которые способность умеет вернуть.

    Args:
        captured: Состояния устройств непосредственно перед действием сценария.

    Returns:
        dict[DeviceId, DeviceStatus]: Состояния для возврата, минимально нужные.
    """
    return {
        device_id: status
        for device_id, status in captured.items()
        if DeviceStatus.restored_by(status) is not None
    }


def scenario_view(scenario: Scenario) -> ScenarioView:
    """Сценарий в форме, которую показывает интерфейс."""
    return ScenarioView(
        id=scenario.id,
        status=scenario.status,
        created_at=scenario.created_at,
        start_at=scenario.start_at,
        duration_minutes=scenario.duration_minutes,
        target=scenario.target,
        completion_behavior=scenario.completion_behavior,
        actions=scenario.actions,
    )


def scenario_payload(scenario: Scenario) -> dict[str, object]:
    """Тело realtime-события об одном сценарии.

    Первое действие разбирается целиком, потому что экрану интересны именно он и
    его цель: сценарий дома сейчас всегда одиночное отложенное действие.
    """
    first = scenario.actions[0] if scenario.actions else None
    return {
        "scenario_id": str(scenario.id),
        "status": scenario.status.value,
        "target": scenario.target,
        "capability": None if first is None else first.capability.value,
        "target_temperature": (
            None
            if first is None or first.target_temperature is None
            else first.target_temperature.celsius
        ),
        "completion_behavior": scenario.completion_behavior.value,
    }
