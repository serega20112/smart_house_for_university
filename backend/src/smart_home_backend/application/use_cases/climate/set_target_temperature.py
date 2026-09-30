"""Set the target temperature."""

from __future__ import annotations

from smart_home_backend.application.interface.services import EventBus
from smart_home_backend.application.interface.unit_of_work import UnitOfWorkFactory
from smart_home_backend.domain.entities.automation import (
    MAX_TEMPERATURE_C,
    MIN_TEMPERATURE_C,
    AutomationSettings,
)
from smart_home_backend.domain.enums.operation import OperationStatus


class SetTargetTemperatureUseCase:
    """Stores the temperature the automation mode aims for."""

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

    async def execute(self, celsius: float) -> tuple[OperationStatus, AutomationSettings | None]:
        """Update the target temperature.

        Args:
            celsius: Requested target temperature.

        Returns:
            tuple[OperationStatus, AutomationSettings | None]: Status and settings.
        """
        if not MIN_TEMPERATURE_C <= celsius <= MAX_TEMPERATURE_C:
            return OperationStatus.INVALID_INPUT, None
        async with self._uow_factory() as uow:
            settings = await uow.automation.get()
            settings.target_temperature = celsius
            saved = await uow.automation.save(settings)
        await self._events.publish("automation.state_changed", _payload(saved))
        return OperationStatus.SUCCESS, saved


def _payload(settings: AutomationSettings) -> dict[str, float | bool]:
    climate_range = settings.temperature_range()
    return {
        "enabled": settings.enabled,
        "target_temperature": settings.target_temperature,
        "min_temperature": climate_range.low,
        "max_temperature": climate_range.high,
    }
