"""Register a new logical device."""

from __future__ import annotations

from backend.application.dto.device import CreateDeviceCommand, DeviceView
from backend.application.ports.events import DomainEventDispatcher, RealtimePublisher
from backend.application.ports.unit_of_work.home import HomeUnitOfWorkFactory
from backend.domain.devices.device import Device
from backend.domain.devices.device_status import DeviceStatus
from backend.domain.devices.relay_channel import RelayChannel
from backend.domain.exceptions import ChannelConflictError
from backend.domain.identifiers import UserId

DEVICES_UPDATED_EVENT = "devices.updated"


class CreateDeviceUseCase:
    """Adds a device bound to a free relay channel of the board."""

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

    async def execute(self, user_id: UserId, command: CreateDeviceCommand) -> DeviceView:
        """Add a device.

        Args:
            user_id: Owner resolved from the session.
            command: Device description.

        Returns:
            DeviceView: The created device, with the status a freshly wired device
            is assumed to have until a board reports otherwise.

        Raises:
            ChannelConflictError: When the relay channel is already wired to
            another device of the same account.
        """
        async with self._home_uow() as uow:
            if await uow.devices.channel_taken(user_id, command.channel):
                raise ChannelConflictError(command.channel)
            device = Device.create(
                user_id=user_id,
                name=command.name,
                kind=command.kind,
                channel=RelayChannel(command.channel),
                capabilities=command.capabilities,
                enabled=command.enabled,
                automation_enabled=command.automation_enabled,
            )
            device.record_change()
            await uow.devices.add(device)
        await self._realtime.publish(
            user_id,
            DEVICES_UPDATED_EVENT,
            {"created": str(device.id), "name": device.name},
        )
        await self._dispatcher.dispatch(device.pull_events())
        return _view_of(device)


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
