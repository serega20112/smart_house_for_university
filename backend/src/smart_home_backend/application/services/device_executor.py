"""Single place where a capability is turned into a relay command.

Manual commands, automation and scenarios all go through this service so the
mapping from capability to physical relay and the publication of device events
live in one spot. Availability of the board is decided by the gateway, which
reports a failed command instead of raising.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from smart_home_backend.application.dto.device import DeviceExecutionResult
from smart_home_backend.application.interface.services import EspGateway, EventBus
from smart_home_backend.application.services.home_runtime import HomeRuntime
from smart_home_backend.domain.entities.device import Device
from smart_home_backend.domain.enums.device import Capability, DeviceStatus
from smart_home_backend.domain.enums.operation import OperationStatus

ACTIVE_CAPABILITY_STATUS: dict[Capability, DeviceStatus] = {
    Capability.ON: DeviceStatus.ON,
    Capability.COOL: DeviceStatus.COOL,
    Capability.HEAT: DeviceStatus.HEAT,
}


class DeviceExecutor:
    """Applies capabilities to relays and publishes the resulting events."""

    def __init__(
        self,
        esp: EspGateway,
        runtime: HomeRuntime,
        events: EventBus,
    ) -> None:
        """Initialize the executor.

        Args:
            esp: Gateway to the physical hardware.
            runtime: Runtime state updated with the outcome.
            events: Publisher of realtime events.

        Returns:
            None.
        """
        self._esp = esp
        self._runtime = runtime
        self._events = events

    async def apply(self, device: Device, capability: Capability) -> DeviceExecutionResult:
        """Apply a capability to a single device.

        Args:
            device: Target device.
            capability: Capability to perform.

        Returns:
            DeviceExecutionResult: Outcome of the command.
        """
        if not device.supports(capability):
            return DeviceExecutionResult(
                status=OperationStatus.UNSUPPORTED, device=device, capability=capability
            )

        outcome = await self._esp.set_relay(device.physical_channel, self._relay_state(capability))
        if not outcome.ok:
            return DeviceExecutionResult(
                status=self._failure_status(outcome.error),
                device=device,
                capability=capability,
            )

        status = ACTIVE_CAPABILITY_STATUS.get(capability, DeviceStatus.OFF)
        self._runtime.apply_relay(device.physical_channel, capability in ACTIVE_CAPABILITY_STATUS)
        self._runtime.remember_mode(device, status)
        await self._events.publish("device.state_changed", self._event_payload(device, status))
        return DeviceExecutionResult(
            status=OperationStatus.SUCCESS, device=device, capability=capability
        )

    async def apply_first_matching(
        self, devices: Sequence[Device], capability: Capability
    ) -> DeviceExecutionResult:
        """Apply a capability to the first enabled device that supports it.

        Args:
            devices: Candidate devices.
            capability: Capability to perform.

        Returns:
            DeviceExecutionResult: Outcome, unsupported when no device matches.
        """
        for device in devices:
            if device.enabled and device.supports(capability):
                return await self.apply(device, capability)
        return DeviceExecutionResult(status=OperationStatus.UNSUPPORTED, capability=capability)

    async def apply_to_all(
        self, devices: Sequence[Device], capability: Capability
    ) -> list[DeviceExecutionResult]:
        """Apply a capability to every device that supports it.

        Args:
            devices: Devices to address.
            capability: Capability to perform.

        Returns:
            list[DeviceExecutionResult]: One outcome per addressed device.
        """
        results: list[DeviceExecutionResult] = []
        for device in devices:
            if device.enabled and device.supports(capability):
                results.append(await self.apply(device, capability))
        return results

    async def restore_statuses(
        self, devices: Sequence[Device], statuses: dict[int, DeviceStatus]
    ) -> list[DeviceExecutionResult]:
        """Bring devices back to previously captured statuses.

        Args:
            devices: Devices to address.
            statuses: Device identifiers mapped to the status to restore.

        Returns:
            list[DeviceExecutionResult]: One outcome per addressed device.
        """
        results: list[DeviceExecutionResult] = []
        by_id = {device.id: device for device in devices}
        for device_id, status in statuses.items():
            device = by_id.get(device_id)
            if device is None:
                continue
            capability = _capability_of(status)
            if capability is None:
                continue
            results.append(await self.apply(device, capability))
        return results

    @staticmethod
    def _relay_state(capability: Capability) -> bool:
        return capability in ACTIVE_CAPABILITY_STATUS

    @staticmethod
    def _failure_status(error: str | None) -> OperationStatus:
        if error == "esp_offline":
            return OperationStatus.UNAVAILABLE
        if error == "unsupported_capability":
            return OperationStatus.UNSUPPORTED
        return OperationStatus.FAILED

    @staticmethod
    def _event_payload(device: Device, status: DeviceStatus) -> dict[str, Any]:
        return {
            "device_id": device.id,
            "name": device.name,
            "channel": device.physical_channel,
            "status": status.value,
        }


def _capability_of(status: DeviceStatus) -> Capability | None:
    return {
        DeviceStatus.ON: Capability.ON,
        DeviceStatus.OFF: Capability.OFF,
        DeviceStatus.COOL: Capability.COOL,
        DeviceStatus.HEAT: Capability.HEAT,
    }.get(status)
