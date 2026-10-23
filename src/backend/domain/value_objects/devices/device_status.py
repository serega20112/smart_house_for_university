"""Logical state of a device.

This is what a device is doing, which is not the same as what a relay contact is
doing: a board that stops answering makes a device unavailable while its last
relay may well still be closed. The questions "is it working" and "can it be
controlled" therefore live here, on the state itself, instead of in a wrapper
object that adds nothing.
"""

from __future__ import annotations

from enum import StrEnum

from backend.domain.value_objects.devices.capability import Capability


class DeviceStatus(StrEnum):
    """What a logical device is currently doing."""

    OFF = "OFF"
    ACTIVE = "ACTIVE"
    COOLING = "COOLING"
    HEATING = "HEATING"
    HUMIDIFYING = "HUMIDIFYING"
    DEHUMIDIFYING = "DEHUMIDIFYING"
    UNAVAILABLE = "UNAVAILABLE"

    @property
    def is_active(self) -> bool:
        """Return whether the device is currently performing an action.

        Returns:
            bool: True for every state in which the device is doing something.
        """
        return self not in (DeviceStatus.OFF, DeviceStatus.UNAVAILABLE)

    @property
    def is_available(self) -> bool:
        """Return whether the device can be controlled at all.

        Returns:
            bool: False when the board behind the device is unreachable.
        """
        return self is not DeviceStatus.UNAVAILABLE

    @classmethod
    def after(cls, capability: Capability) -> DeviceStatus:
        """Return the state a device reaches by performing a capability.

        The mapping lives in one table, so a capability without a resulting state
        is a missing row rather than a rule spread over the model.

        Args:
            capability: Capability that was performed.

        Returns:
            DeviceStatus: Resulting logical state.

        Raises:
            KeyError: When the capability has no resulting state.
        """
        return RESULTING_STATUS[capability]

    @classmethod
    def restored_by(cls, status: DeviceStatus) -> Capability | None:
        """Return the capability that puts a device back into a given state.

        Args:
            status: State the device should return to.

        Returns:
            Capability | None: Capability to perform, or None when the state
            describes something no capability produces.
        """
        return RESTORING_CAPABILITY.get(status)


RESULTING_STATUS: dict[Capability, DeviceStatus] = {
    Capability.ON: DeviceStatus.ACTIVE,
    Capability.OFF: DeviceStatus.OFF,
    Capability.COOL: DeviceStatus.COOLING,
    Capability.HEAT: DeviceStatus.HEATING,
    Capability.HUMIDIFY: DeviceStatus.HUMIDIFYING,
    Capability.DEHUMIDIFY: DeviceStatus.DEHUMIDIFYING,
}

RESTORING_CAPABILITY: dict[DeviceStatus, Capability] = {
    status: capability for capability, status in RESULTING_STATUS.items()
}
