"""Infrastructure layer.

Adapters for everything the application talks to: the database, the board, the
notification channels and the natural language pipeline.
"""

from smart_home_backend.infrastructure.clock import SystemClock
from smart_home_backend.infrastructure.database import (
    SqlUnitOfWork,
    build_engine,
    build_session_factory,
    create_schema,
)
from smart_home_backend.infrastructure.di import Container, build_container
from smart_home_backend.infrastructure.esp import EspConnection, EspGatewayAdapter
from smart_home_backend.infrastructure.logging_config import configure_logging, get_logger
from smart_home_backend.infrastructure.nlp import build_command_parser, build_intent_classifier
from smart_home_backend.infrastructure.telegram import TelegramBotRunner, TelegramNotifier

__all__ = [
    "Container",
    "EspConnection",
    "EspGatewayAdapter",
    "SqlUnitOfWork",
    "SystemClock",
    "TelegramBotRunner",
    "TelegramNotifier",
    "build_command_parser",
    "build_container",
    "build_engine",
    "build_intent_classifier",
    "build_session_factory",
    "configure_logging",
    "create_schema",
    "get_logger",
]
