"""Read a single device."""

from __future__ import annotations

from smart_home_backend.application.interface.unit_of_work import UnitOfWorkFactory
from smart_home_backend.domain.entities.device import Device


class GetDeviceUseCase:
    """Returns one configured device."""

    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        """Initialize the use case.

        Args:
            uow_factory: Factory producing units of work.

        Returns:
            None.
        """
        self._uow_factory = uow_factory

    async def execute(self, device_id: int) -> Device | None:
        """Return a device by id.

        Args:
            device_id: Identifier of the device.

        Returns:
            Device | None: Device or None when it does not exist.
        """
        async with self._uow_factory() as uow:
            return await uow.devices.get(device_id)
