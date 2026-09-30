"""Read the active scenarios."""

from __future__ import annotations

from smart_home_backend.application.interface.unit_of_work import UnitOfWorkFactory
from smart_home_backend.domain.entities.scenario import Scenario


class GetActiveScenariosUseCase:
    """Returns the scenarios currently occupying the control priority."""

    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        """Initialize the use case.

        Args:
            uow_factory: Factory producing units of work.

        Returns:
            None.
        """
        self._uow_factory = uow_factory

    async def execute(self) -> list[Scenario]:
        """Return the pending and running scenarios.

        Returns:
            list[Scenario]: Active scenarios.
        """
        async with self._uow_factory() as uow:
            return list(await uow.scenarios.list_active())
