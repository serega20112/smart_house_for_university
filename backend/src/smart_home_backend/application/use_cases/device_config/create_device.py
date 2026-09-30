"""Create a logical device."""

from __future__ import annotations

from smart_home_backend.application.dto.device import CreateDeviceCommand
from smart_home_backend.application.interface.services import EventBus
from smart_home_backend.application.interface.unit_of_work import UnitOfWorkFactory
from smart_home_backend.domain.entities.device import Device
from smart_home_backend.domain.enums.device import parse_capability, parse_device_type
from smart_home_backend.domain.enums.operation import OperationStatus


class CreateDeviceUseCase:
    """Registers a new logical device on a free relay channel."""

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
        self, command: CreateDeviceCommand
    ) -> tuple[OperationStatus, Device | None]:
        """Create a device bound to the requested relay channel.

        Args:
            command: Device description.

        Returns:
            tuple[OperationStatus, Device | None]: Status and the created device.
        """
        capabilities = frozenset(
            capability
            for capability in (parse_capability(name) for name in command.capabilities)
            if capability is not None
        )
        async with self._uow_factory() as uow:
            if await uow.devices.channel_in_use(command.physical_channel):
                return OperationStatus.CHANNEL_CONFLICT, None
            device = Device(
                id=0,
                name=command.name,
                type=parse_device_type(command.type),
                physical_channel=command.physical_channel,
                capabilities=capabilities,
                enabled=command.enabled,
                automation_enabled=command.automation_enabled,
            )
            saved = await uow.devices.save(device)
        await self._events.publish("devices.updated", {"created": saved.id})
        return OperationStatus.SUCCESS, saved
