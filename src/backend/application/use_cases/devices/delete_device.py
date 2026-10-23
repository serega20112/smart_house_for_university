"""Remove a logical device."""

from __future__ import annotations

from backend.application.errors import DeviceNotFoundError
from backend.application.interface.services.home_state_store import HomeStateStore
from backend.application.interface.services.realtime_publisher import RealtimePublisher
from backend.application.interface.unit_of_work.home import HomeUnitOfWorkFactory
from backend.domain.events import EventName
from backend.domain.identifiers import DeviceId, UserId


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
        await self._realtime.publish(
            user_id, EventName.DEVICES_UPDATED, {"deleted": str(device_id)}
        )
