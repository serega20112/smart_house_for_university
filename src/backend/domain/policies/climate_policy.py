"""What the climate of a home is asking for.

A demand is a decision of the model, and the capability that satisfies it is part
of that decision. Humidifying used to be spelled as "switch the humidifier on",
which quietly made a humidifier with a target level impossible; naming the demand
and its capability keeps the two apart.
"""

from __future__ import annotations

from enum import StrEnum

from backend.domain.value_objects.climate.climate_band import ClimateBand
from backend.domain.value_objects.climate.climate_reading import ClimateReading
from backend.domain.value_objects.devices.capability import Capability


class ClimateDemand(StrEnum):
    """An action required to bring the climate back inside the band."""

    COOL = "COOL"
    HEAT = "HEAT"
    HUMIDIFY = "HUMIDIFY"
    DEHUMIDIFY = "DEHUMIDIFY"

    @property
    def capability(self) -> Capability:
        """Return the capability that satisfies the demand.

        Returns:
            Capability: Capability to ask a device for.
        """
        return DEMAND_CAPABILITIES[self]


DEMAND_CAPABILITIES: dict[ClimateDemand, Capability] = {
    ClimateDemand.COOL: Capability.COOL,
    ClimateDemand.HEAT: Capability.HEAT,
    ClimateDemand.HUMIDIFY: Capability.HUMIDIFY,
    ClimateDemand.DEHUMIDIFY: Capability.DEHUMIDIFY,
}


class DemandCalculator:
    """Turns a reading and a configuration into the demands it produces.

    The calculator is a domain service rather than a module of functions because
    it needs both climate bands and both readings to answer, and because a caller
    should not be able to apply half of the rule.
    """

    def demands_for(
        self,
        temperature_band: ClimateBand[object] | None,
        humidity_band: ClimateBand[object] | None,
        reading: ClimateReading,
    ) -> tuple[ClimateDemand, ...]:
        """Return every demand the current reading produces.

        A missing measurement produces no demand rather than a guess, and both
        dimensions are evaluated even when only one of them is configured.

        Args:
            temperature_band: Acceptable temperature band or None when the
                temperature is not automated.
            humidity_band: Acceptable humidity band or None when the humidity is
                not automated.
            reading: Current sensor reading.

        Returns:
            tuple[ClimateDemand, ...]: Demands to act on, empty when every
            measured value already sits inside its band.
        """
        demands: list[ClimateDemand] = []
        temperature = reading.temperature
        if temperature is not None and temperature_band is not None:
            if temperature_band.needs_decrease(temperature):
                demands.append(ClimateDemand.COOL)
            elif temperature_band.needs_increase(temperature):
                demands.append(ClimateDemand.HEAT)
        humidity = reading.humidity
        if humidity is not None and humidity_band is not None:
            if humidity_band.needs_increase(humidity):
                demands.append(ClimateDemand.HUMIDIFY)
            elif humidity_band.needs_decrease(humidity):
                demands.append(ClimateDemand.DEHUMIDIFY)
        return tuple(demands)

    def capability_towards(
        self, target_celsius: float, current_celsius: float | None
    ) -> Capability:
        """Return the capability that moves the home towards a target temperature.

        Without a measurement the request is taken as cooling, because a person
        asking for a temperature is normally asking for a cooler room.

        Args:
            target_celsius: Requested target temperature.
            current_celsius: Measured temperature or None when unavailable.

        Returns:
            Capability: Cooling or heating capability.
        """
        if current_celsius is None or target_celsius < current_celsius:
            return Capability.COOL
        return Capability.HEAT
