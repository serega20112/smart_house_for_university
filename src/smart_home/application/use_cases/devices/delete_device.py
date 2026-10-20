"""Remove a logical device."""

from __future__ import annotations

from smart_home.application.errors import DeviceNotFoundError
from smart_home.application.ports.events import RealtimePublisher
from smart_home.application.ports.services import HomeStateStore
from smart_home.application.ports.unit_of_work.home import HomeUnitOfWorkFactory
from smart_home.domain.identifiers import DeviceId, UserId

DEVICES_UPDATED_EVENT = "devices.updated"


class DeleteDeviceUseCase:
    """Removes a device and forgets everything the runtime knew about it."""

    def __init__(
        self,
        home_uow: HomeUnitOfWorkFactory,
        state_store: HomeStateStore,
        realtime: RealtimePublisher,
    ) -> None:
        """Initialize the use case.

        Args:
            home_uow: Factory producing transactions over the configuration.
            state_store: Durable home of the volatile state.
            realtime: Publisher of events to the open clients.

        Returns:
            None.
        """
        self._home_uow = home_uow
        self._state_store = state_store
        self._realtime = realtime

    async def execute(self, user_id: UserId, device_id: DeviceId) -> None:
        """Delete a device.

        Args:
            user_id: Owner resolved from the session.
            device_id: Identifier of the device.

        Returns:
            None.

        Raises:
            DeviceNotFoundError: When the account has no such device.
        """
        async with self._home_uow() as uow:
            removed = await uow.devices.delete(user_id, device_id)
        if not removed:
            raise DeviceNotFoundError(device_id)
        await self._state_store.forget_device_status(user_id, device_id)
        await self._realtime.publish(user_id, DEVICES_UPDATED_EVENT, {"deleted": str(device_id)})
