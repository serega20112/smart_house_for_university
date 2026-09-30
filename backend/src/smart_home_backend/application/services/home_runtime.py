"""In-memory runtime state of the home.

Single source of truth about the current relay and sensor values, kept in sync
with the board. It also remembers the logical modes of climate devices, which
cannot be observed from a relay alone, and the manual override window that
suspends automation.

The class is intentionally not thread safe: all access happens inside one
asyncio loop.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from smart_home_backend.application.interface.services import Clock
from smart_home_backend.domain.entities.device import Device
from smart_home_backend.domain.entities.home import ClimateReading, HomeState
from smart_home_backend.domain.enums.device import RELAY_CHANNEL_COUNT, DeviceStatus


class HomeRuntime:
    """Live state of the home mirrored from the board."""

    def __init__(self, clock: Clock) -> None:
        """Initialize the runtime.

        Args:
            clock: Clock used for the manual override window.

        Returns:
            None.
        """
        self._clock = clock
        self.state = HomeState()
        self._device_mode: dict[int, DeviceStatus] = {}
        self._override_until: datetime | None = None

    def apply_relay_states(self, states: list[bool]) -> list[int]:
        """Apply reported relay states and report which channels changed.

        Args:
            states: Relay states ordered by channel.

        Returns:
            list[int]: Channels whose state changed.
        """
        changed: list[int] = []
        for index, on in enumerate(states, start=1):
            if not 1 <= index <= RELAY_CHANNEL_COUNT:
                continue
            if self.state.is_relay_on(index) != bool(on):
                self.state.set_relay(index, bool(on))
                changed.append(index)
        self.state.touch()
        return changed

    def apply_relay(self, channel: int, on: bool) -> None:
        """Apply a single relay state optimistically after a command.

        Args:
            channel: Physical relay channel.
            on: New relay state.

        Returns:
            None.
        """
        self.state.set_relay(channel, on)
        self.state.touch()

    def apply_reading(
        self, temperature: float | None, humidity: float | None
    ) -> tuple[bool, bool]:
        """Apply reported sensor values and report what changed.

        Args:
            temperature: Measured temperature or None.
            humidity: Measured relative humidity or None.

        Returns:
            tuple[bool, bool]: Temperature and humidity change flags.
        """
        temperature_changed = temperature is not None and temperature != self.state.temperature
        humidity_changed = humidity is not None and humidity != self.state.humidity
        self.state.set_reading(temperature, humidity)
        return temperature_changed, humidity_changed

    def set_esp_online(self, online: bool) -> None:
        """Update the board availability.

        Args:
            online: Whether the board is reachable.

        Returns:
            None.
        """
        if online:
            self.state.mark_esp_online()
        else:
            self.state.mark_esp_offline()

    @property
    def esp_online(self) -> bool:
        """Return whether the board is reachable.

        Returns:
            bool: True when the board is connected.
        """
        return self.state.esp_online

    @property
    def reading(self) -> ClimateReading:
        """Return the current sensor reading.

        Returns:
            ClimateReading: Typed reading of the current values.
        """
        return self.state.to_reading()

    def device_status(self, device: Device) -> DeviceStatus:
        """Return the current logical status of a device.

        Args:
            device: Device to inspect.

        Returns:
            DeviceStatus: Current status of the device.
        """
        if not self.state.esp_online:
            return DeviceStatus.UNAVAILABLE
        if not self.state.is_relay_on(device.physical_channel):
            return DeviceStatus.OFF
        return self._device_mode.get(device.id, DeviceStatus.ON)

    def remember_mode(self, device: Device, status: DeviceStatus) -> None:
        """Store the logical mode commanded to a device.

        Args:
            device: Affected device.
            status: Commanded logical status.

        Returns:
            None.
        """
        self._device_mode[device.id] = status

    def forget_mode(self, device_id: int) -> None:
        """Drop the remembered mode of a device.

        Args:
            device_id: Identifier of the device.

        Returns:
            None.
        """
        self._device_mode.pop(device_id, None)

    def set_manual_override(self, minutes: int) -> None:
        """Suspend automation for the requested duration.

        Args:
            minutes: Override duration in minutes.

        Returns:
            None.
        """
        self._override_until = self._clock.now() + timedelta(minutes=max(0, minutes))

    def clear_manual_override(self) -> None:
        """End the manual override window immediately.

        Returns:
            None.
        """
        self._override_until = None

    def is_manual_override(self) -> bool:
        """Return whether automation is currently suspended by manual control.

        Returns:
            bool: True inside the override window.
        """
        return self._override_until is not None and self._clock.now() < self._override_until

    def snapshot(self) -> dict[str, Any]:
        """Return the runtime values as a plain dictionary.

        Returns:
            dict[str, Any]: Serializable snapshot of the runtime state.
        """
        return {
            "esp_online": self.state.esp_online,
            "manual_override": self.is_manual_override(),
            "temperature": self.state.temperature,
            "humidity": self.state.humidity,
        }
