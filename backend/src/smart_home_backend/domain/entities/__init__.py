"""Domain entities package."""

from smart_home_backend.domain.entities.automation import AutomationSettings
from smart_home_backend.domain.entities.device import Device
from smart_home_backend.domain.entities.home import ClimateReading, HomeState, Relay, Sensor
from smart_home_backend.domain.entities.scenario import Scenario, ScenarioAction

__all__ = [
    "AutomationSettings",
    "ClimateReading",
    "Device",
    "HomeState",
    "Relay",
    "Scenario",
    "ScenarioAction",
    "Sensor",
]
