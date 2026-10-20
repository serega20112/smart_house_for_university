"""Change an existing logical device."""

from __future__ import annotations

from smart_home.application.dto.device import DeviceView, UpdateDeviceCommand
from smart_home.application.errors import (
    ConcurrentModificationError,
    DeviceNotFoundError,
)
from smart_home.application.ports.events import DomainEventDispatcher, RealtimePublisher
from smart_home.application.ports.unit_of_work.home import HomeUnitOfWorkFactory
from smart_home.domain.devices.device import Device
from smart_home.domain.devices.device_status import DeviceStatus
from smart_home.domain.devices.relay_channel import RelayChannel
from smart_home.domain.identifiers import DeviceId, UserId

DEVICES_UPDATED_EVENT = "devices.updated"
REFRESH_ATTEMPTS = 3


class UpdateDeviceUseCase:
    """Applies a partial change to a device."""

    def __init__(
        self,
        home_uow: HomeUnitOfWorkFactory,
        realtime: RealtimePublisher,
        dispatcher: DomainEventDispatcher,
    ) -> None:
        """Initialize the use case.

        Args:
            home_uow: Factory producing transactions over the configuration.
            realtime: Publisher of events to the open clients.
            dispatcher: Announces the fact that the configuration changed.

        Returns:
            None.
        """
        self._home_uow = home_uow
        self._realtime = realtime
        self._dispatcher = dispatcher

    async def execute(
        self, user_id: UserId, device_id: DeviceId, command: UpdateDeviceCommand
    ) -> DeviceView:
        """Change a device on a fresh snapshot of the configuration.

        The lookup is scoped to the owner, so a device of another account reads
        as missing instead of being modified. A change that loses a race with
        another writer is retried on the newest snapshot, so the user does not
        have to repeat themselves because another tab touched the same device a
        moment earlier.

        Args:
            user_id: Owner resolved from the session.
            device_id: Identifier of the device.
            command: Fields to change.

        Returns:
            DeviceView: The updated device.

        Raises:
            DeviceNotFoundError: When the account has no such device.
            ChannelConflictError: When the new channel is already wired.
            ConcurrentModificationError: When others keep winning the race.
        """
        stored: Device | ConcurrentModificationError = await self._attempt(
            user_id, device_id, command
        )
        for _ in range(REFRESH_ATTEMPTS - 1):
            if not isinstance(stored, ConcurrentModificationError):
                break
            stored = await self._attempt(user_id, device_id, command)
        if isinstance(stored, ConcurrentModificationError):
            raise stored
        device = stored
        await self._realtime.publish(user_id, DEVICES_UPDATED_EVENT, {"updated": str(device_id)})
        await self._dispatcher.dispatch(device.pull_events())
        return _view_of(device)

    async def _attempt(
        self, user_id: UserId, device_id: DeviceId, command: UpdateDeviceCommand
    ) -> Device | ConcurrentModificationError:
        """State the change once on the snapshot the transaction reads.

        Args:
            user_id: Owner resolved from the session.
            device_id: Identifier of the device.
            command: Fields to change.

        Returns:
            Device | ConcurrentModificationError: The updated device, or the
            race this attempt lost.
        """
        async with self._home_uow() as uow:
            device = await uow.devices.get(user_id, device_id)
            if device is None:
                raise DeviceNotFoundError(device_id)
            try:
                device.reconfigure(
                    name=command.name,
                    kind=command.kind,
                    channel=(None if command.channel is None else RelayChannel(command.channel)),
                    capabilities=command.capabilities,
                    enabled=command.enabled,
                    automation_enabled=command.automation_enabled,
                )
                device.record_change()
                await uow.devices.update(device)
            except ConcurrentModificationError as lost:
                return lost
            return device


def _view_of(device: Device) -> DeviceView:
    return DeviceView(
        id=device.id,
        name=device.name,
        kind=device.kind,
        channel=int(device.channel),
        capabilities=device.capabilities,
        enabled=device.enabled,
        automation_enabled=device.automation_enabled,
        status=DeviceStatus.OFF,
    )
