"""Мапперы сценария, его действий и снятых состояний."""

from __future__ import annotations

from uuid import uuid4

from backend.domain.aggregates.scenario.scenario import Scenario
from backend.domain.entities.scenario.scenario_action import ScenarioAction
from backend.domain.identifiers import DeviceId, ScenarioId, UserId
from backend.domain.value_objects.climate.temperature import Temperature
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.domain.value_objects.scenario.completion_behavior import CompletionBehavior
from backend.domain.value_objects.scenario.scenario_status import ScenarioStatus
from backend.infrastructure.database.mappers.base import as_utc
from backend.infrastructure.database.models import (
    ScenarioActionModel,
    ScenarioCapturedStatusModel,
    ScenarioModel,
)


def scenario_to_row(scenario: Scenario) -> ScenarioModel:
    """Строит строку, описывающую отложенный сценарий.

    Args:
        scenario: Сценарий для сериализации.

    Returns:
        ScenarioModel: Новая строка, описывающая сценарий.
    """
    return ScenarioModel(
        id=scenario.id.value,
        user_id=scenario.user_id.value,
        status=scenario.status.value,
        created_at=scenario.created_at,
        start_at=scenario.start_at,
        duration_minutes=scenario.duration_minutes,
        target=scenario.target,
        completion_behavior=scenario.completion_behavior.value,
        version=scenario.version,
    )


def scenario_from_row(
    row: ScenarioModel,
    actions: tuple[ScenarioAction, ...],
    captured_statuses: dict[DeviceId, DeviceStatus],
) -> Scenario:
    """Строит сценарий, описанный его строкой и строками коллекций.

    Args:
        row: Строка для десериализации.
        actions: Действия, прочитанные из ``scenario_actions``.
        captured_statuses: Состояния, прочитанные из ``scenario_captured_statuses``.

    Returns:
        Scenario: Восстановленный сценарий.
    """
    return Scenario(
        id=ScenarioId.parse(row.id),
        user_id=UserId.parse(row.user_id),
        status=ScenarioStatus(row.status),
        created_at=as_utc(row.created_at),
        start_at=as_utc(row.start_at),
        duration_minutes=row.duration_minutes,
        target=row.target,
        completion_behavior=CompletionBehavior(row.completion_behavior),
        actions=actions,
        captured_statuses=captured_statuses,
        version=row.version,
    )


def action_rows(scenario: Scenario) -> list[ScenarioActionModel]:
    """Строит по строке на каждое действие сценария.

    Действие называет способность и цель, а не канал реле, и своей идентичности в модели
    не имеет, поэтому хранилище выдаёт её само и порядком записывает явно.

    Args:
        scenario: Сценарий для сериализации.

    Returns:
        list[ScenarioActionModel]: Строки действий в порядке, объявленном сценарием.
    """
    return [
        ScenarioActionModel(
            id=uuid4(),
            scenario_id=scenario.id.value,
            position=position,
            capability=action.capability.value,
            target_temperature=(
                None if action.target_temperature is None else action.target_temperature.celsius
            ),
        )
        for position, action in enumerate(scenario.actions)
    ]


def action_from_row(row: ScenarioActionModel) -> ScenarioAction:
    """Строит действие сценария, описанное строкой.

    Args:
        row: Строка для десериализации.

    Returns:
        ScenarioAction: Восстановленное действие.
    """
    return ScenarioAction(
        capability=Capability.parse(row.capability),
        target_temperature=(
            None if row.target_temperature is None else Temperature(row.target_temperature)
        ),
    )


def captured_status_rows(scenario: Scenario) -> list[ScenarioCapturedStatusModel]:
    """Строит по строке на каждое состояние, снятое до начала сценария.

    Args:
        scenario: Сценарий для сериализации.

    Returns:
        list[ScenarioCapturedStatusModel]: Строки снятых состояний сценария.
    """
    return [
        ScenarioCapturedStatusModel(
            scenario_id=scenario.id.value,
            device_id=device_id.value,
            status=status.value,
        )
        for device_id, status in scenario.captured_statuses.items()
    ]


def captured_status_from_row(row: ScenarioCapturedStatusModel) -> tuple[DeviceId, DeviceStatus]:
    """Строит снятое состояние устройства, описанное строкой.

    Args:
        row: Строка для десериализации.

    Returns:
        tuple[DeviceId, DeviceStatus]: Устройство, чьё состояние снимали, и само
        состояние.
    """
    return DeviceId.parse(row.device_id), DeviceStatus(row.status)
