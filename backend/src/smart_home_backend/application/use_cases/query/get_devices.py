"""Read the configured devices."""

from __future__ import annotations

from smart_home_backend.application.interface.unit_of_work import UnitOfWorkFactory
from smart_home_backend.domain.entities.device import Device


class GetDevicesUseCase:
    """Returns every configured device."""

    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        """Initialize the use case.

        Args:
            uow_factory: Factory producing units of work.

        Returns:
            None.
        """
        self._uow_factory = uow_factory

    async def execute(self) -> list[Device]:
        """Return all configured devices.

        Returns:
            list[Device]: Configured devices.
        """
        async with self._uow_factory() as uow:
            return list(await uow.devices.list_all())
