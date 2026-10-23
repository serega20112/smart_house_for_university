"""Live state of one home, mirrored from its board.

The aggregate is deterministic: it never reads the clock. Every method that
changes the state is told when the change happened, which is what makes the whole
home reproducible in a test and free of hidden side effects.

It is also pure data with behaviour, not a cache: it holds what the board last
reported and what was commanded to it, and it answers questions about the two
without knowing about sockets, sessions or storage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from backend.domain.aggregates.device.device import Device
from backend.domain.identifiers import DeviceId, UserId
from backend.domain.value_objects.climate.climate_reading import ClimateReading
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.domain.value_objects.devices.relay_state import RelayState


@dataclass
class HomeState:
    """Everything known about the physical layer of one home.

    Args:
        user_id: Owner of the home.
        relay_states: Position of every relay channel.
        reading: Last measurement of the climate sensors.
        board_online: Whether the board is reachable.
        device_modes: Logical mode commanded to each device.
        manual_override_until: Moment the manual override window closes.
        changed_at: Moment of the last change.

    Returns:
        None.
    """

    user_id: UserId
    relay_states: dict[int, RelayState] = field(default_factory=dict)
    reading: ClimateReading = field(default_factory=ClimateReading)
    board_online: bool = False
    device_modes: dict[DeviceId, DeviceStatus] = field(default_factory=dict)
    manual_override_until: datetime | None = None
    changed_at: datetime | None = None

    def is_relay_closed(self, channel: int) -> bool:
        """Return whether a relay contact is energized.

        Args:
            channel: Relay channel number.

        Returns:
            bool: True when the contact is closed.
        """
        return self.relay_states.get(channel) is RelayState.ON

    def apply_relay_report(self, states: list[bool], changed_at: datetime) -> tuple[int, ...]:
        """Apply the relay positions reported by the board.

        Args:
            states: Contact positions ordered by channel, starting at one.
            changed_at: Moment the board reported them.

        Returns:
            tuple[int, ...]: Channels whose position actually changed.
        """
        changed: list[int] = []
        for index, energized in enumerate(states, start=1):
            if self.is_relay_closed(index) is bool(energized):
                continue
            self.relay_states[index] = RelayState.ON if energized else RelayState.OFF
            changed.append(index)
        self.changed_at = changed_at
        return tuple(changed)

    def apply_command(self, device: Device, status: DeviceStatus, changed_at: datetime) -> None:
        """Record a command that was confirmed by the board.

        Args:
            device: Affected device.
            status: State the device was driven into.
            changed_at: Moment of the confirmation.

        Returns:
            None.
        """
        self.relay_states[int(device.channel)] = (
            RelayState.ON if status.is_active else RelayState.OFF
        )
        self.device_modes[device.id] = status
        self.changed_at = changed_at

    def apply_reading(self, reading: ClimateReading, changed_at: datetime) -> ClimateReading:
        """Apply a sensor report, keeping the values it could not measure.

        Args:
            reading: Measured values, absent where the sensor did not answer.
            changed_at: Moment of the report.

        Returns:
            ClimateReading: The values that actually changed.
        """
        previous = self.reading
        self.reading = ClimateReading(
            temperature=(
                previous.temperature if reading.temperature is None else reading.temperature
            ),
            humidity=previous.humidity if reading.humidity is None else reading.humidity,
        )
        self.changed_at = changed_at
        return ClimateReading(
            temperature=(
                self.reading.temperature
                if self.reading.temperature != previous.temperature
                else None
            ),
            humidity=(
                self.reading.humidity if self.reading.humidity != previous.humidity else None
            ),
        )

    def set_board_available(self, online: bool, changed_at: datetime) -> None:
        """Record whether the board is reachable.

        Args:
            online: True when the board answered.
            changed_at: Moment of the transition.

        Returns:
            None.
        """
        self.board_online = online
        if not online:
            self.device_modes.clear()
        self.changed_at = changed_at

    def status_of(self, device: Device) -> DeviceStatus:
        """Return the logical state of a device right now.

        Args:
            device: Device to inspect.

        Returns:
            DeviceStatus: State the device is in.
        """
        return self.status_for(device.id, int(device.channel))

    def status_for(self, device_id: DeviceId, channel: int) -> DeviceStatus:
        """Return the logical state of a device by its identity and its channel.

        Args:
            device_id: Identifier of the device.
            channel: Relay channel the device is wired to.

        Returns:
            DeviceStatus: State the device is in.
        """
        if not self.board_online:
            return DeviceStatus.UNAVAILABLE
        if not self.is_relay_closed(channel):
            return DeviceStatus.OFF
        return self.device_modes.get(device_id, DeviceStatus.ACTIVE)

    def forget_device(self, device_id: DeviceId) -> None:
        """Drop everything remembered about a device that no longer exists.

        Args:
            device_id: Identifier of the removed device.

        Returns:
            None.
        """
        self.device_modes.pop(device_id, None)

    def suspend_automation_until(self, moment: datetime) -> None:
        """Keep automation away until a moment.

        Args:
            moment: Moment the override window closes.

        Returns:
            None.
        """
        self.manual_override_until = moment

    def resume_automation(self) -> None:
        """End the manual override window immediately.

        Returns:
            None.
        """
        self.manual_override_until = None

    def is_automation_suspended(self, now: datetime) -> bool:
        """Return whether automation is currently held back by manual control.

        Args:
            now: Moment to judge at.

        Returns:
            bool: True inside the override window.
        """
        return self.manual_override_until is not None and now < self.manual_override_until

    def suspend_automation_for(self, now: datetime, minutes: int) -> None:
        """Hold automation back for a number of minutes.

        Args:
            now: Moment the manual action happened at.
            minutes: Length of the window.

        Returns:
            None.
        """
        self.manual_override_until = now + timedelta(minutes=max(0, minutes))
