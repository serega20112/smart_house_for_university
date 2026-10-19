"""Turning a capability into a relay command.

Every path that changes the hardware goes through this service: a person in the
browser, a command in the messenger, automation and scenarios alike. That is what
keeps one rule in one place instead of four copies of it.

The service does not decide what a manual action means for the rest of the system.
It performs the capability, records the fact on the aggregate and hands the facts to
the dispatcher; suspending automation and telling the interface are reactions other
components subscribe to, which is why they are written once.
"""

from __future__ import annotations

from collections.abc import Sequence

from backend.application.dto.device import CapabilityReport, DeviceView
from backend.application.errors import BoardUnreachableError, DeviceNotFoundError
from backend.application.ports.boards import BoardGateway
from backend.application.ports.events import DomainEventDispatcher, RealtimePublisher
from backend.application.ports.services import Clock, HomeStateStore
from backend.application.ports.unit_of_work.home import HomeUnitOfWorkFactory
from backend.domain.devices.capability import Capability
from backend.domain.devices.device import Device
from backend.domain.devices.device_status import DeviceStatus
from backend.domain.exceptions import NoDeviceForCapabilityError
from backend.domain.identifiers import DeviceId, UserId
from backend.domain.services.device_selector import DeviceSelector

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
            await uow.devices.update(device)
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
        driven: list[DeviceView] = []
        for device in self._selector.all_supporting(devices, capability):
            status = await self._perform(user_id, device, capability, manual)
            driven.append(_view_of(device, status))
        return CapabilityReport(capability=capability, devices=tuple(driven))

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
            await self._perform(user_id, device, capability, manual=False)

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
        state = await self._state_store.load(user_id)
        return [_view_of(device, state.status_of(device)) for device in devices]

    async def _perform(
        self,
        user_id: UserId,
        device: Device,
        capability: Capability,
        manual: bool,
    ) -> DeviceStatus:
        device.require_capability(capability)
        status = device.drive(capability, source_is_manual=manual)
        result = await self._boards.set_relay(
            user_id, device.id, int(device.channel), capability.energizes_relay
        )
        if not result.accepted:
            raise BoardUnreachableError(result.reason or "unknown")

        now = self._clock.now()
        state = await self._state_store.load(user_id)
        state.apply_command(device, status, now)
        await self._state_store.save(state)
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
        return status


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
