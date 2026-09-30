"""In-memory aggregate of the current home state.

The aggregate mirrors the last known relay states and sensor readings received
from the board. Whether the board is reachable affects device states, which is
why availability lives here instead of in a service.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from smart_home_backend.domain.entities.home.climate_reading import ClimateReading
from smart_home_backend.domain.enums.device import RELAY_CHANNEL_COUNT, RelayState
from smart_home_backend.domain.value_objects.climate.humidity import Humidity
from smart_home_backend.domain.value_objects.climate.temperature import Temperature


@dataclass
class HomeState:
    """Latest known state of the physical layer.

    Args:
        relay_states: State of every relay channel.
        temperature: Last measured temperature in degrees Celsius.
        humidity: Last measured relative humidity in percent.
        esp_online: Whether the board is currently reachable.
        last_updated_at: Timestamp of the last update.

    Returns:
        None.
    """

    relay_states: dict[int, RelayState] = field(
        default_factory=lambda: {
            channel: RelayState.OFF for channel in range(1, RELAY_CHANNEL_COUNT + 1)
        }
    )
    temperature: float | None = None
    humidity: float | None = None
    esp_online: bool = False
    last_updated_at: datetime | None = None

    def is_relay_on(self, channel: int) -> bool:
        """Return whether a relay channel is energized.

        Args:
            channel: Relay channel number.

        Returns:
            bool: True when the relay is on.
        """
        return self.relay_states.get(channel) is RelayState.ON

    def set_relay(self, channel: int, on: bool) -> None:
        """Update a single relay channel.

        Args:
            channel: Relay channel number.
            on: New relay state.

        Returns:
            None.
        """
        self.relay_states[channel] = RelayState.ON if on else RelayState.OFF

    def set_reading(self, temperature: float | None, humidity: float | None) -> None:
        """Update sensor values, keeping the previous ones for missing fields.

        Args:
            temperature: New temperature or None to keep the current value.
            humidity: New humidity or None to keep the current value.

        Returns:
            None.
        """
        if temperature is not None:
            self.temperature = temperature
        if humidity is not None:
            self.humidity = humidity
        self.touch()

    def to_reading(self) -> ClimateReading:
        """Return the current values as typed value objects.

        Returns:
            ClimateReading: Typed reading.
        """
        temperature = Temperature(self.temperature) if self.temperature is not None else None
        humidity = Humidity(self.humidity) if self.humidity is not None else None
        return ClimateReading(temperature=temperature, humidity=humidity)

    def mark_esp_online(self) -> None:
        """Mark the board as reachable.

        Returns:
            None.
        """
        self.esp_online = True
        self.touch()

    def mark_esp_offline(self) -> None:
        """Mark the board as unreachable.

        Returns:
            None.
        """
        self.esp_online = False
        self.touch()

    def touch(self) -> None:
        """Refresh the update timestamp.

        Returns:
            None.
        """
        self.last_updated_at = datetime.now(timezone.utc)
