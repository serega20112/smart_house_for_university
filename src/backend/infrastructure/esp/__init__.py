"""Инфраструктура общения с платами.

``protocol``
    кадры wire-протокола как проверенные модели Pydantic.
``session``
    сеанс одной платы, её команды в ожидании подтверждения и реестр плат.
``handshake``
    разбор первого кадра: путь, ключ, владелец или предложение о плате.
``inbound``
    перевод входящего кадра в вызовы приёмника состояния дома.
``connection``
    WebSocket-сервер, к которому дозваниваются платы, и дверь к их командам.
``onboarding``
    операции прикладного слоя, которые поднимает handshake.
``adapters``
    фасад, с которым говорит прикладной слой.

Транспорт получает всё нужное через конструктор: приёмник сообщений и шлюз
сопряжения. После сборки ничего не подвязывается, поэтому сеанс платы полностью
описывается её аргументами, и тест собирает его без сокета.
"""

from backend.infrastructure.esp.adapters import BoardGatewayAdapter
from backend.infrastructure.esp.connection import EspConnection
from backend.infrastructure.esp.onboarding import (
    BoardAnnouncement,
    BoardIdentity,
    BoardOnboardingGateway,
)
from backend.infrastructure.esp.protocol import (
    AckFrame,
    ClaimedFrame,
    ClaimFrame,
    ErrorFrame,
    GetStateFrame,
    HelloFrame,
    InboundFrame,
    MalformedFrameError,
    OutboundFrame,
    RejectedFrame,
    SensorDataFrame,
    SetRelayFrame,
    StateFrame,
    parse_inbound,
)
from backend.infrastructure.esp.session import BoardSession

__all__ = [
    "AckFrame",
    "BoardAnnouncement",
    "BoardGatewayAdapter",
    "BoardIdentity",
    "BoardOnboardingGateway",
    "BoardSession",
    "ClaimFrame",
    "ClaimedFrame",
    "ErrorFrame",
    "EspConnection",
    "GetStateFrame",
    "HelloFrame",
    "InboundFrame",
    "MalformedFrameError",
    "OutboundFrame",
    "RejectedFrame",
    "SensorDataFrame",
    "SetRelayFrame",
    "StateFrame",
    "parse_inbound",
]
