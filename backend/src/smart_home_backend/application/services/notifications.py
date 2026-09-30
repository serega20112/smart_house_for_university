"""Notification texts for significant home events.

Keeping the wording in one module makes it easy to review every message the user
can receive and to keep them consistent across channels.
"""

from __future__ import annotations

from smart_home_backend.domain.entities.scenario import Scenario

GOAL_REACHED = "цель достигнута"
DURATION_EXPIRED = "истёк тайминг"


def scenario_started(scenario: Scenario) -> str:
    """Return the notification shown when a scenario starts.

    Args:
        scenario: Started scenario.

    Returns:
        str: Notification text.
    """
    return f"Сценарий #{scenario.id} запущен."


def scenario_summary(scenario: Scenario, temperature: float | None) -> str:
    """Return the periodic progress notification of a running scenario.

    Args:
        scenario: Running scenario.
        temperature: Current temperature or None when unavailable.

    Returns:
        str: Notification text.
    """
    value = "нет данных" if temperature is None else f"{temperature:.1f}°C"
    return f"Сценарий #{scenario.id} выполняется, температура {value}."


def scenario_completed(scenario: Scenario, reason: str) -> str:
    """Return the notification shown when a scenario finishes.

    Args:
        scenario: Completed scenario.
        reason: Why the scenario finished.

    Returns:
        str: Notification text.
    """
    return f"Сценарий #{scenario.id} завершён: {reason}."


def scenario_failed(scenario: Scenario, reason: str) -> str:
    """Return the notification shown when a scenario fails.

    Args:
        scenario: Failed scenario.
        reason: Why the scenario failed.

    Returns:
        str: Notification text.
    """
    return f"Сценарий #{scenario.id} завершился с ошибкой: {reason}."


def esp_connected() -> str:
    """Return the notification shown when the board comes online.

    Returns:
        str: Notification text.
    """
    return "ESP8266 подключилась."


def esp_disconnected() -> str:
    """Return the notification shown when the board goes offline.

    Returns:
        str: Notification text.
    """
    return "ESP8266 отключилась — устройства недоступны."
