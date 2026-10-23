"""Мапперы сценария, его действий и снятых состояний."""

from __future__ import annotations

from uuid import uuid4

from backend.domain.aggregates.scenario.scenario import Scenario
from backend.domain.identifiers import DeviceId, ScenarioId, UserId
from backend.domain.value_objects.climate.temperature import Temperature
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.domain.value_objects.scenario.completion_behavior import CompletionBehavior
from backend.domain.value_objects.scenario.scenario_action import ScenarioAction
from backend.domain.value_objects.scenario.scenario_status import ScenarioStatus
from backend.infrastructure.database.mappers.base import as_utc
from backend.infrastructure.database.tables import (
    ScenarioActionRow,
    ScenarioCapturedStatusRow,
    ScenarioRow,
)


def scenario_to_row(scenario: Scenario) -> ScenarioRow:
    """Build the row describing a timed scenario.

    Args:
        scenario: Scenario to serialize.

    Returns:
        ScenarioRow: New row describing the scenario.
    """
    return ScenarioRow(
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
    row: ScenarioRow,
    actions: tuple[ScenarioAction, ...],
    captured_statuses: dict[DeviceId, DeviceStatus],
) -> Scenario:
    """Build the scenario a row and its collection rows describe.

    Args:
        row: Row to deserialize.
        actions: Actions read from ``scenario_actions``.
        captured_statuses: States read from ``scenario_captured_statuses``.

    Returns:
        Scenario: Restored scenario.
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


def action_rows(scenario: Scenario) -> list[ScenarioActionRow]:
    """Build one row per action of a scenario.

    An action names a capability and a target rather than a relay channel, and it
    has no identity of its own in the model, so the store assigns one and records
    the order explicitly.

    Args:
        scenario: Scenario to serialize.

    Returns:
        list[ScenarioActionRow]: Action rows in the order the scenario declares.
    """
    return [
        ScenarioActionRow(
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


def action_from_row(row: ScenarioActionRow) -> ScenarioAction:
    """Build the scenario action a row describes.

    Args:
        row: Row to deserialize.

    Returns:
        ScenarioAction: Restored action.
    """
    return ScenarioAction(
        capability=Capability.parse(row.capability),
        target_temperature=(
            None if row.target_temperature is None else Temperature(row.target_temperature)
        ),
    )


def captured_status_rows(scenario: Scenario) -> list[ScenarioCapturedStatusRow]:
    """Build one row per device state captured before a scenario started.

    Args:
        scenario: Scenario to serialize.

    Returns:
        list[ScenarioCapturedStatusRow]: Captured state rows of the scenario.
    """
    return [
        ScenarioCapturedStatusRow(
            scenario_id=scenario.id.value,
            device_id=device_id.value,
            status=status.value,
        )
        for device_id, status in scenario.captured_statuses.items()
    ]


def captured_status_from_row(row: ScenarioCapturedStatusRow) -> tuple[DeviceId, DeviceStatus]:
    """Build the captured device state a row describes.

    Args:
        row: Row to deserialize.

    Returns:
        tuple[DeviceId, DeviceStatus]: Device the state was captured for and the
        state itself.
    """
    return DeviceId.parse(row.device_id), DeviceStatus(row.status)
