"""Set the target humidity."""

from __future__ import annotations

from smart_home_backend.application.interface.services import EventBus
from smart_home_backend.application.interface.unit_of_work import UnitOfWorkFactory
from smart_home_backend.domain.entities.automation import (
    MAX_HUMIDITY_PERCENT,
    MIN_HUMIDITY_PERCENT,
    AutomationSettings,
)
from smart_home_backend.domain.enums.operation import OperationStatus


class SetTargetHumidityUseCase:
    """Stores the humidity the automation mode aims for."""

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

    async def execute(self, percent: float) -> tuple[OperationStatus, AutomationSettings | None]:
        """Update the target humidity.

        Args:
            percent: Requested target humidity.

        Returns:
            tuple[OperationStatus, AutomationSettings | None]: Status and settings.
        """
        if not MIN_HUMIDITY_PERCENT <= percent <= MAX_HUMIDITY_PERCENT:
            return OperationStatus.INVALID_INPUT, None
        async with self._uow_factory() as uow:
            settings = await uow.automation.get()
            settings.target_humidity = percent
            saved = await uow.automation.save(settings)
        await self._events.publish("automation.state_changed", _payload(saved))
        return OperationStatus.SUCCESS, saved


def _payload(settings: AutomationSettings) -> dict[str, float | bool]:
    climate_range = settings.humidity_range()
    return {
        "enabled": settings.enabled,
        "target_humidity": settings.target_humidity,
        "min_humidity": climate_range.low,
        "max_humidity": climate_range.high,
    }
