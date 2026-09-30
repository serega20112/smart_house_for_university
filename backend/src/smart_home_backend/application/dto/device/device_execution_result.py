"""Result of a single device command."""

from __future__ import annotations

from dataclasses import dataclass

from smart_home_backend.domain.entities.device import Device
from smart_home_backend.domain.enums.device import Capability
from smart_home_backend.domain.enums.operation import OperationStatus


@dataclass(frozen=True, slots=True)
class DeviceExecutionResult:
    """Outcome of applying a capability to one device.

    Args:
        status: Result class of the execution.
        device: Affected device or None when nothing was addressed.
        capability: Capability that was requested.

    Returns:
        None.
    """

    status: OperationStatus
    device: Device | None = None
    capability: Capability | None = None

    @property
    def ok(self) -> bool:
        """Return whether the command reached the device.

        Returns:
            bool: True on success.
        """
        return self.status.is_success
