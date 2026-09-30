"""Ports of the application layer.

Contracts for repositories, external services and the transaction boundary live
here. The domain itself only knows its own language and declares no ports.
"""

from smart_home_backend.application.interface.repositories import (
    AutomationRepository,
    DeviceRepository,
    ScenarioRepository,
)
from smart_home_backend.application.interface.services import (
    Clock,
    CommandOutcome,
    CommandParser,
    EspGateway,
    EspStateHandler,
    EventBus,
    IntentClassifier,
    IntentPrediction,
    Notifier,
    ParsedCommand,
)
from smart_home_backend.application.interface.unit_of_work import UnitOfWork, UnitOfWorkFactory

__all__ = [
    "AutomationRepository",
    "Clock",
    "CommandOutcome",
    "CommandParser",
    "DeviceRepository",
    "EspGateway",
    "EspStateHandler",
    "EventBus",
    "IntentClassifier",
    "IntentPrediction",
    "Notifier",
    "ParsedCommand",
    "ScenarioRepository",
    "UnitOfWork",
    "UnitOfWorkFactory",
]
