"""Delete a logical device."""

from __future__ import annotations

from smart_home_backend.application.interface.services import EventBus
from smart_home_backend.application.interface.unit_of_work import UnitOfWorkFactory
from smart_home_backend.application.services import HomeRuntime
from smart_home_backend.domain.enums.operation import OperationStatus


class DeleteDeviceUseCase:
    """Removes a device and forgets its runtime mode."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        events: EventBus,
        runtime: HomeRuntime,
    ) -> None:
        """Initialize the use case.

        Args:
            uow_factory: Factory producing units of work.
            events: Publisher of realtime events.
            runtime: Runtime state holding the remembered device modes.

        Returns:
            None.
        """
        self._uow_factory = uow_factory
        self._events = events
        self._runtime = runtime

    async def execute(self, device_id: int) -> OperationStatus:
        """Delete a device.

        Args:
            device_id: Identifier of the device.

        Returns:
            OperationStatus: Outcome of the deletion.
        """
        async with self._uow_factory() as uow:
            deleted = await uow.devices.delete(device_id)
        if not deleted:
            return OperationStatus.NOT_FOUND
        self._runtime.forget_mode(device_id)
        await self._events.publish("devices.updated", {"deleted": device_id})
        return OperationStatus.SUCCESS
