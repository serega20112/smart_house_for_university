"""Update the automation settings."""

from __future__ import annotations

from smart_home_backend.application.dto.automation import UpdateAutomationCommand
from smart_home_backend.application.interface.services import EventBus
from smart_home_backend.application.interface.unit_of_work import UnitOfWorkFactory
from smart_home_backend.domain.entities.automation import AutomationSettings
from smart_home_backend.domain.enums.operation import OperationStatus


class UpdateAutomationUseCase:
    """Applies a partial update to the automation configuration."""

    def __init__(self, uow_factory: UnitOfWorkFactory, events: EventBus) -> None:
        """Initialize the use case.

        Args:
            uow_factory: Factory producing units of work.
            events: Publisher of realtime events.

        Returns:
            None.
        """
        self._uow_factory = uow_factory
        self._events = events

    async def execute(
        self, command: UpdateAutomationCommand
    ) -> tuple[OperationStatus, AutomationSettings | None]:
        """Update the automation settings and announce the change.

        Args:
            command: Fields to change.

        Returns:
            tuple[OperationStatus, AutomationSettings | None]: Status and settings.
        """
        async with self._uow_factory() as uow:
            settings = await uow.automation.get()
            _apply_changes(settings, command)
            saved = await uow.automation.save(settings)
        await self._events.publish("automation.state_changed", automation_payload(saved))
        return OperationStatus.SUCCESS, saved


def _apply_changes(settings: AutomationSettings, command: UpdateAutomationCommand) -> None:
    if command.enabled is not None:
        settings.enabled = command.enabled
    if command.target_temperature is not None:
        settings.target_temperature = command.target_temperature
    if command.temperature_tolerance is not None:
        settings.temperature_tolerance = abs(command.temperature_tolerance)
    if command.target_humidity is not None:
        settings.target_humidity = command.target_humidity
    if command.humidity_tolerance is not None:
        settings.humidity_tolerance = abs(command.humidity_tolerance)
    if command.participating_device_ids is not None:
        settings.participating_device_ids = frozenset(command.participating_device_ids)


def automation_payload(settings: AutomationSettings) -> dict[str, float | bool | list[int]]:
    """Return the realtime payload describing the automation settings.

    Args:
        settings: Settings to describe.

    Returns:
        dict[str, float | bool | list[int]]: Serializable payload.
    """
    temperature_range = settings.temperature_range()
    humidity_range = settings.humidity_range()
    return {
        "enabled": settings.enabled,
        "target_temperature": settings.target_temperature,
        "min_temperature": temperature_range.low,
        "max_temperature": temperature_range.high,
        "target_humidity": settings.target_humidity,
        "min_humidity": humidity_range.low,
        "max_humidity": humidity_range.high,
        "participating_device_ids": sorted(settings.participating_device_ids),
    }
