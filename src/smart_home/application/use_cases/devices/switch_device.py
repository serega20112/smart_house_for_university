"""Switch devices on behalf of a person."""

from __future__ import annotations

from smart_home.application.dto.device import CapabilityReport, DeviceView
from smart_home.application.ports.unit_of_work.home import HomeUnitOfWorkFactory
from smart_home.application.services.device_control import DeviceControlService
from smart_home.domain.devices.capability import Capability
from smart_home.domain.identifiers import DeviceId, UserId


class SwitchDeviceUseCase:
    """Applies one capability to one device.

    Turning a device on, turning it off and putting it into a mode are the same
    operation with a different capability, so there is one use case instead of
    three copies of it.
    """

    def __init__(self, home_uow: HomeUnitOfWorkFactory, control: DeviceControlService) -> None:
        """Initialize the use case.

        Args:
            home_uow: Factory producing transactions over the configuration.
            control: Service performing capabilities against the hardware.

        Returns:
            None.
        """
        self._home_uow = home_uow
        self._control = control

    async def execute(
        self, user_id: UserId, device_id: DeviceId, capability: Capability
    ) -> DeviceView:
        """Switch a device.

        Args:
            user_id: Owner resolved from the session.
            device_id: Identifier of the device.
            capability: Capability to perform.

        Returns:
            DeviceView: The device with the status it reached.

        Raises:
            DeviceNotFoundError: When the account has no such device.
            UnsupportedCapabilityError: When the device cannot perform it.
            BoardUnreachableError: When the board did not confirm.
        """
        return await self._control.apply_to_device(user_id, device_id, capability)


class SwitchAllDevicesUseCase:
    """Applies one capability to every device able to perform it."""

    def __init__(self, home_uow: HomeUnitOfWorkFactory, control: DeviceControlService) -> None:
        """Initialize the use case.

        Args:
            home_uow: Factory producing transactions over the configuration.
            control: Service performing capabilities against the hardware.

        Returns:
            None.
        """
        self._home_uow = home_uow
        self._control = control

    async def execute(self, user_id: UserId, capability: Capability) -> CapabilityReport:
        """Switch every device that supports the capability.

        Args:
            user_id: Owner resolved from the session.
            capability: Capability to perform.

        Returns:
            CapabilityReport: Devices that were driven.
        """
        async with self._home_uow() as uow:
            devices = list(await uow.devices.list_all(user_id))
        return await self._control.apply_to_all(user_id, devices, capability)
