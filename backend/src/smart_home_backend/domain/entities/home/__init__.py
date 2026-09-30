"""Physical layer entities package."""

from smart_home_backend.domain.entities.home.climate_reading import ClimateReading
from smart_home_backend.domain.entities.home.home_state import HomeState
from smart_home_backend.domain.entities.home.relay import Relay
from smart_home_backend.domain.entities.home.sensor import Sensor

__all__ = ["ClimateReading", "HomeState", "Relay", "Sensor"]
