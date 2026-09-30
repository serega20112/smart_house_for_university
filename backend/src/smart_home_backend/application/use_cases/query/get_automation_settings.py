"""Read the automation settings."""

from __future__ import annotations

from smart_home_backend.application.interface.unit_of_work import UnitOfWorkFactory
from smart_home_backend.domain.entities.automation import AutomationSettings


class GetAutomationSettingsUseCase:
    """Returns the current automation configuration."""

    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        """Initialize the use case.

        Args:
            uow_factory: Factory producing units of work.

        Returns:
            None.
        """
        self._uow_factory = uow_factory

    async def execute(self) -> AutomationSettings:
        """Return the automation settings.

        Returns:
            AutomationSettings: Stored settings or defaults when absent.
        """
        async with self._uow_factory() as uow:
            return await uow.automation.get()
