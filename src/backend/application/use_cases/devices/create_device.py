"""Add a new logical device.

Raises:
    ChannelConflictError: When the relay channel is already connected to
        another device of the same account.
"""

from __future__ import annotations

from backend.application.dto.devices.create_device_command import CreateDeviceCommand
from backend.application.dto.views.device_view import DeviceView
from backend.application.interfaces.services.messaging.domain_event_dispatcher import (
    DomainEventDispatcher,
)
from backend.application.interfaces.services.messaging.realtime_publisher import RealtimePublisher
from backend.application.interfaces.services.state.home_state_store import HomeStateStore
from backend.application.interfaces.unit_of_work.home import HomeUnitOfWorkFactory
from backend.domain.aggregates.device.device import Device
from backend.domain.events import EventName
from backend.domain.identifiers import UserId
from backend.domain.value_objects.devices.relay_channel import RelayChannel


class CreateDeviceUseCase:
    """Adds a device bound to a free relay board channel."""

    def __init__(
        self,
        home_uow: HomeUnitOfWorkFactory,
        realtime: RealtimePublisher,
        dispatcher: DomainEventDispatcher,
        state_store: HomeStateStore,
    ) -> None:
        """Initialize the use case.

        Args:
            home_uow: Factory for transactions over the configuration.
            realtime: Publisher of events to open connections.
            dispatcher: Declares a fact of configuration change.
            state_store: Reliable store of mutable state.
        """
        self._home_uow = home_uow
        self._realtime = realtime
        self._dispatcher = dispatcher
        self._state_store = state_store

    async def execute(self, user_id: UserId, command: CreateDeviceCommand) -> DeviceView:
        """Add a device.

        Args:
            user_id: Owner authorised from the session.
            command: Device description.

        Returns:
            DeviceView: Created device with current state from mutable state.

        Raises:
            ChannelConflictError: When relay channel is already connected to
                another device of the same account.
        """
        async with self._home_uow() as uow:
            device = Device.create(
                user_id=user_id,
                name=command.name,
                kind=command.kind,
                channel=RelayChannel(command.channel),
                capabilities=command.capabilities,
                board_id=command.board_id,
                enabled=command.enabled,
                automation_enabled=command.automation_enabled,
            )
            device.record_change()
            await uow.devices.add(device)
            await uow.commit()
        await self._realtime.publish(
            user_id,
            EventName.DEVICES_UPDATED,
            {"created": str(device.id), "name": device.name},
        )
        await self._dispatcher.dispatch(device.pull_events())
        state = await self._state_store.read(user_id)
        return DeviceView.of(device, state.status_of(device))
