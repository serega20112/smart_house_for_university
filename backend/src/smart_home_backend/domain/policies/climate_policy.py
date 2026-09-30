"""Climate decision policy with hysteresis.

Pure functions without infrastructure dependencies: automation settings and a
reading come in, the required capabilities come out.
"""

from __future__ import annotations

from smart_home_backend.domain.entities.automation import AutomationSettings
from smart_home_backend.domain.entities.home import ClimateReading
from smart_home_backend.domain.enums.base import StrEnum
from smart_home_backend.domain.enums.device import Capability


class ClimateDemand(StrEnum):
    """Climate action required to bring the home back into the target band."""

    NONE = "NONE"
    COOL = "COOL"
    HEAT = "HEAT"
    HUMIDIFY = "HUMIDIFY"
    DEHUMIDIFY = "DEHUMIDIFY"

    @property
    def capability(self) -> Capability | None:
        """Return the capability that satisfies the demand.

        Returns:
            Capability | None: Capability or None when nothing has to be done.
        """
        return DEMAND_CAPABILITIES.get(self)


DEMAND_CAPABILITIES: dict[ClimateDemand, Capability] = {
    ClimateDemand.COOL: Capability.COOL,
    ClimateDemand.HEAT: Capability.HEAT,
    ClimateDemand.HUMIDIFY: Capability.ON,
}


def evaluate_temperature(
    settings: AutomationSettings, reading: ClimateReading
) -> ClimateDemand:
    """Return the temperature demand for the current reading.

    Args:
        settings: Automation settings.
        reading: Current sensor reading.

    Returns:
        ClimateDemand: Required demand.
    """
    if reading.temperature is None:
        return ClimateDemand.NONE
    climate_range = settings.temperature_range()
    value = reading.temperature.celsius
    if climate_range.needs_decrease(value):
        return ClimateDemand.COOL
    if climate_range.needs_increase(value):
        return ClimateDemand.HEAT
    return ClimateDemand.NONE


def evaluate_humidity(settings: AutomationSettings, reading: ClimateReading) -> ClimateDemand:
    """Return the humidity demand for the current reading.

    Args:
        settings: Automation settings.
        reading: Current sensor reading.

    Returns:
        ClimateDemand: Required demand.
    """
    if reading.humidity is None:
        return ClimateDemand.NONE
    climate_range = settings.humidity_range()
    value = reading.humidity.percent
    if climate_range.needs_increase(value):
        return ClimateDemand.HUMIDIFY
    if climate_range.needs_decrease(value):
        return ClimateDemand.DEHUMIDIFY
    return ClimateDemand.NONE


def evaluate(settings: AutomationSettings, reading: ClimateReading) -> list[ClimateDemand]:
    """Return every demand the current reading produces.

    Args:
        settings: Automation settings.
        reading: Current sensor reading.

    Returns:
        list[ClimateDemand]: Demands to act on, empty when all values are in band.
    """
    demands = [evaluate_temperature(settings, reading), evaluate_humidity(settings, reading)]
    return [demand for demand in demands if demand is not ClimateDemand.NONE]


def capability_for_target(
    current_temperature: float | None, target_temperature: float
) -> Capability:
    """Return the capability that moves the home towards a target temperature.

    Args:
        current_temperature: Measured temperature or None when unavailable.
        target_temperature: Requested target temperature.

    Returns:
        Capability: Cooling or heating capability.
    """
    if current_temperature is None or target_temperature < current_temperature:
        return Capability.COOL
    return Capability.HEAT
