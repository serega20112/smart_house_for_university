"""Logical state of a device."""

from __future__ import annotations

from dataclasses import dataclass

from smart_home_backend.domain.enums.device import DeviceStatus

ACTIVE_STATUSES: frozenset[DeviceStatus] = frozenset(
    {DeviceStatus.ON, DeviceStatus.COOL, DeviceStatus.HEAT}
)


@dataclass(frozen=True, slots=True)
class DeviceState:
    """Current logical state of a device.

    Args:
        status: Device status.

    Returns:
        None.
    """

    status: DeviceStatus

    @classmethod
    def unavailable(cls) -> "DeviceState":
        """Build a state describing an unreachable device.

        Returns:
            DeviceState: Unavailable state.
        """
        return cls(DeviceStatus.UNAVAILABLE)

    @property
    def is_active(self) -> bool:
        """Return whether the device is currently performing an action.

        Returns:
            bool: True for on, cooling and heating states.
        """
        return self.status in ACTIVE_STATUSES

    @property
    def is_available(self) -> bool:
        """Return whether the device can be controlled.

        Returns:
            bool: False when the board is unreachable.
        """
        return self.status is not DeviceStatus.UNAVAILABLE
