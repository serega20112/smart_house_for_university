"""Turning a capability into a relay command.

Every path that changes the hardware goes through this service: a person in the
browser, a command in the messenger, automation and scenarios alike. That is what
keeps one rule in one place instead of four copies of it.

The order of the steps is fixed. The aggregate is loaded and the transaction is
closed before the hardware is asked; the board is commanded while no database
connection is held; a fresh short transaction then stores the confirmed state;
and only after that transaction commits the fact is published to the interface
and handed to the reactions. A refused command therefore leaves the database, the
events and the volatile state untouched.

The service does not decide what a manual action means for the rest of the system.
Suspending automation is a reaction other components subscribe to, which is why
it is written once.
"""

from __future__ import annotations

from collections.abc import Sequence

from smart_home.application.dto.device import CapabilityReport, DeviceView
from smart_home.application.errors import BoardUnreachableError, DeviceNotFoundError
from smart_home.application.ports.boards import BoardGateway
from smart_home.application.ports.events import DomainEventDispatcher, RealtimePublisher
from smart_home.application.ports.services import Clock, HomeStateStore
from smart_home.application.ports.unit_of_work.home import HomeUnitOfWorkFactory
from smart_home.domain.devices.capability import Capability
from smart_home.domain.devices.device import Device
from smart_home.domain.devices.device_status import DeviceStatus
from smart_home.domain.exceptions import NoDeviceForCapabilityError
from smart_home.domain.identifiers import DeviceId, UserId
from smart_home.domain.services.device_selector import DeviceSelector

CAPABILITY_APPLIED_EVENT = "device.state_changed"


class DeviceControlService:
    """Applies capabilities to devices and keeps the runtime state in step."""

    def __init__(
        self,
        home_uow: HomeUnitOfWorkFactory,
        boards: BoardGateway,
        state_store: HomeStateStore,
        realtime: RealtimePublisher,
        dispatcher: DomainEventDispatcher,
        clock: Clock,
        selector: DeviceSelector,
    ) -> None:
        """Initialize the service.

        Args:
            home_uow: Factory producing transactions over the configuration.
            boards: Gateway to the physical hardware.
            state_store: Durable home of the volatile state.
            realtime: Publisher of events to the open clients.
            dispatcher: Hands recorded facts to their subscribers.
            clock: Source of the current time.
            selector: Resolves devices by capability.

        Returns:
            None.
        """
        self._home_uow = home_uow
        self._boards = boards
        self._state_store = state_store
        self._realtime = realtime
        self._dispatcher = dispatcher
        self._clock = clock
        self._selector = selector

    async def apply_to_device(
        self,
        user_id: UserId,
        device_id: DeviceId,
        capability: Capability,
        *,
        manual: bool = True,
    ) -> DeviceView:
        """Apply a capability to one device.

        Args:
            user_id: Owner of the device and of the board.
            device_id: Identifier of the device.
            capability: Capability to perform.
            manual: Whether a person asked for it.

        Returns:
            DeviceView: The device with the status it reached.

        Raises:
            DeviceNotFoundError: When the account has no such device.
            NoDeviceForCapabilityError: When the device cannot perform it.
            BoardUnreachableError: When the board did not confirm.
        """
        async with self._home_uow() as uow:
            device = await uow.devices.get(user_id, device_id)
            if device is None:
                raise DeviceNotFoundError(device_id)

        status = await self._perform(user_id, device, capability, manual)
        await self._persist(user_id, device)
        await self._announce(user_id, device, status)
        return _view_of(device, status)

    async def apply_to_first_matching(
        self,
        user_id: UserId,
        devices: Sequence[Device],
        capability: Capability,
        *,
        manual: bool = True,
    ) -> DeviceView:
        """Apply a capability to the first device able to perform it.

        Args:
            user_id: Owner of the devices and of the board.
            devices: Candidate devices.
            capability: Capability to perform.
            manual: Whether a person asked for it.

        Returns:
            DeviceView: The device that was driven.

        Raises:
            NoDeviceForCapabilityError: When nothing in the home supports it.
        """
        target = self._selector.first_supporting(devices, capability)
        if target is None:
            raise NoDeviceForCapabilityError(capability.value)
        status = await self._perform(user_id, target, capability, manual)
        await self._persist(user_id, target)
        await self._announce(user_id, target, status)
        return _view_of(target, status)

    async def apply_to_all(
        self,
        user_id: UserId,
        devices: Sequence[Device],
        capability: Capability,
        *,
        manual: bool = True,
    ) -> CapabilityReport:
        """Apply a capability to every device able to perform it.

        A board that refuses one command does not stop the others: the caller gets a
        report of what was driven, which is more useful than an exception in the
        middle of a sweep.

        Args:
            user_id: Owner of the devices and of the board.
            devices: Devices to address.
            capability: Capability to perform.
            manual: Whether a person asked for it.

        Returns:
            CapabilityReport: Devices that were driven.
        """
        driven: list[tuple[Device, DeviceStatus]] = []
        for device in self._selector.all_supporting(devices, capability):
            status = await self._perform(user_id, device, capability, manual)
            driven.append((device, status))
        await self._persist(user_id, *(device for device, _status in driven))
        for device, status in driven:
            await self._announce(user_id, device, status)
        return CapabilityReport(
            capability=capability,
            devices=tuple(_view_of(device, status) for device, status in driven),
        )

    async def restore_statuses(
        self, user_id: UserId, devices: Sequence[Device], wanted: dict[DeviceId, DeviceStatus]
    ) -> None:
        """Put devices back into states they had before.

        Args:
            user_id: Owner of the devices and of the board.
            devices: Devices to address.
            wanted: Target state per device.

        Returns:
            None.
        """
        by_id = {device.id: device for device in devices}
        for device_id, status in wanted.items():
            device = by_id.get(device_id)
            capability = DeviceStatus.restored_by(status)
            if device is None or capability is None:
                continue
            restored = await self._perform(user_id, device, capability, manual=False)
            await self._persist(user_id, device)
            await self._announce(user_id, device, restored)

    async def views_with_live_status(
        self, user_id: UserId, devices: Sequence[Device]
    ) -> list[DeviceView]:
        """Return the devices with the status they have right now.

        Args:
            user_id: Owner of the devices.
            devices: Configured devices.

        Returns:
            list[DeviceView]: Devices with their live status.
        """
        state = await self._state_store.read(user_id)
        return [_view_of(device, state.status_of(device)) for device in devices]

    async def _perform(
        self,
        user_id: UserId,
        device: Device,
        capability: Capability,
        manual: bool,
    ) -> DeviceStatus:
        """Decide and drive, holding no transaction while the board answers.

        Args:
            user_id: Owner of the board.
            device: Device the capability is performed on.
            capability: Capability to perform.
            manual: Whether a person asked for it.

        Returns:
            DeviceStatus: State the device reached.

        Raises:
            UnsupportedCapabilityError: When the device cannot perform it.
            BoardUnreachableError: When the board did not confirm.
        """
        device.require_capability(capability)
        status = device.drive(capability, source_is_manual=manual)
        result = await self._boards.set_relay(
            user_id, device.id, int(device.channel), capability.energizes_relay
        )
        if not result.accepted:
            device.pull_events()
            raise BoardUnreachableError(result.reason or "unknown")

        await self._state_store.record_command_result(user_id, device, status, self._clock.now())
        return status

    async def _persist(self, user_id: UserId, *devices: Device) -> None:
        """Store the aggregates in one short transaction.

        Args:
            user_id: Owner of the devices.
            devices: Aggregates to store; every one was already confirmed.

        Returns:
            None.
        """
        async with self._home_uow() as uow:
            for device in devices:
                await uow.devices.update(device)

    async def _announce(self, user_id: UserId, device: Device, status: DeviceStatus) -> None:
        """Publish the fact once it is committed.

        Args:
            user_id: Owner of the device.
            device: Device the fact belongs to.
            status: State the device was driven into.

        Returns:
            None.
        """
        await self._realtime.publish(
            user_id,
            CAPABILITY_APPLIED_EVENT,
            {
                "device_id": str(device.id),
                "name": device.name,
                "channel": int(device.channel),
                "status": status.value,
            },
        )
        await self._dispatcher.dispatch(device.pull_events())


def _view_of(device: Device, status: DeviceStatus) -> DeviceView:
    return DeviceView(
        id=device.id,
        name=device.name,
        kind=device.kind,
        channel=int(device.channel),
        capabilities=device.capabilities,
        enabled=device.enabled,
        automation_enabled=device.automation_enabled,
        status=status,
    )
