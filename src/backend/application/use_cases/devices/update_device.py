"""Change an existing logical device."""

from __future__ import annotations

from backend.application.dto.device import DeviceView, UpdateDeviceCommand
from backend.application.errors import DeviceNotFoundError
from backend.application.ports.events import DomainEventDispatcher, RealtimePublisher
from backend.application.ports.unit_of_work.home import HomeUnitOfWorkFactory
from backend.domain.devices.device_status import DeviceStatus
from backend.domain.devices.relay_channel import RelayChannel
from backend.domain.exceptions import ChannelConflictError
from backend.domain.identifiers import DeviceId, UserId

DEVICES_UPDATED_EVENT = "devices.updated"


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
        """Change a device, refusing a channel another device already holds.

        The lookup is scoped to the owner, so a device of another account reads as
        missing instead of being modified.

        Args:
            user_id: Owner resolved from the session.
            device_id: Identifier of the device.
            command: Fields to change.

        Returns:
            DeviceView: The updated device.

        Raises:
            DeviceNotFoundError: When the account has no such device.
            ChannelConflictError: When the new channel is already wired.
        """
        async with self._home_uow() as uow:
            device = await uow.devices.get(user_id, device_id)
            if device is None:
                raise DeviceNotFoundError(device_id)
            if (
                command.channel is not None
                and command.channel != int(device.channel)
                and await uow.devices.channel_taken(user_id, command.channel, exclude=device_id)
            ):
                raise ChannelConflictError(command.channel)
            device.reconfigure(
                name=command.name,
                kind=command.kind,
                channel=None if command.channel is None else RelayChannel(command.channel),
                capabilities=command.capabilities,
                enabled=command.enabled,
                automation_enabled=command.automation_enabled,
            )
            device.record_change()
            await uow.devices.update(device)
        await self._realtime.publish(
            user_id, DEVICES_UPDATED_EVENT, {"updated": str(device_id)}
        )
        await self._dispatcher.dispatch(device.pull_events())
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
