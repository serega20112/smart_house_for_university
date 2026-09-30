"""Automation settings package."""

from smart_home_backend.domain.entities.automation.automation_settings import (
    MAX_HUMIDITY_PERCENT,
    MAX_TEMPERATURE_C,
    MIN_HUMIDITY_PERCENT,
    MIN_TEMPERATURE_C,
    AutomationSettings,
)

__all__ = [
    "MAX_HUMIDITY_PERCENT",
    "MAX_TEMPERATURE_C",
    "MIN_HUMIDITY_PERCENT",
    "MIN_TEMPERATURE_C",
    "AutomationSettings",
]
