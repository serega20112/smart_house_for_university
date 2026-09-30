"""Update a logical device."""

from __future__ import annotations

from smart_home_backend.application.dto.device import UpdateDeviceCommand
from smart_home_backend.application.interface.services import EventBus
from smart_home_backend.application.interface.unit_of_work import UnitOfWorkFactory
from smart_home_backend.domain.entities.device import Device
from smart_home_backend.domain.enums.device import parse_capability, parse_device_type
from smart_home_backend.domain.enums.operation import OperationStatus


class UpdateDeviceUseCase:
    """Applies a partial update to an existing device."""

    def __init__(self, uow_factory: UnitOfWorkFactory, events: EventBus) -> None:
        """Initialize the use case.

        Args:
            uow_factory: Factory producing units of work.
            events: Publisher of realtime events.

        Returns:
            None.
        """
        self._uow_factory = uow_factory
        self._events = events

    async def execute(
        self, device_id: int, command: UpdateDeviceCommand
    ) -> tuple[OperationStatus, Device | None]:
        """Update a device, rejecting a channel already taken by another one.

        Args:
            device_id: Identifier of the device.
            command: Fields to change.

        Returns:
            tuple[OperationStatus, Device | None]: Status and the updated device.
        """
        async with self._uow_factory() as uow:
            device = await uow.devices.get(device_id)
            if device is None:
                return OperationStatus.NOT_FOUND, None
            if command.physical_channel is not None and (
                command.physical_channel != device.physical_channel
                and await uow.devices.channel_in_use(
                    command.physical_channel, exclude_id=device_id
                )
            ):
                return OperationStatus.CHANNEL_CONFLICT, None
            _apply_changes(device, command)
            saved = await uow.devices.save(device)
        await self._events.publish("devices.updated", {"updated": saved.id})
        return OperationStatus.SUCCESS, saved


def _apply_changes(device: Device, command: UpdateDeviceCommand) -> None:
    if command.name is not None:
        device.name = command.name
    if command.type is not None:
        device.type = parse_device_type(command.type)
    if command.physical_channel is not None:
        device.physical_channel = command.physical_channel
    if command.capabilities is not None:
        device.capabilities = frozenset(
            capability
            for capability in (parse_capability(name) for name in command.capabilities)
            if capability is not None
        )
    if command.enabled is not None:
        device.enabled = command.enabled
    if command.automation_enabled is not None:
        device.automation_enabled = command.automation_enabled
