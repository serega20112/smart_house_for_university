"""Toggle the automation mode."""

from __future__ import annotations

from smart_home_backend.application.interface.services import EventBus
from smart_home_backend.application.interface.unit_of_work import UnitOfWorkFactory
from smart_home_backend.application.use_cases.automation.update_automation import (
    automation_payload,
)
from smart_home_backend.domain.entities.automation import AutomationSettings
from smart_home_backend.domain.enums.operation import OperationStatus


class ToggleAutomationUseCase:
    """Switches the climate automation on or off."""

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

    async def execute(self, enabled: bool) -> tuple[OperationStatus, AutomationSettings]:
        """Enable or disable the automation mode.

        Args:
            enabled: Desired state of the automation mode.

        Returns:
            tuple[OperationStatus, AutomationSettings]: Status and the settings.
        """
        async with self._uow_factory() as uow:
            settings = await uow.automation.get()
            settings.enabled = enabled
            saved = await uow.automation.save(settings)
        await self._events.publish("automation.state_changed", automation_payload(saved))
        return OperationStatus.SUCCESS, saved
