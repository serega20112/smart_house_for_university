"""Транспорт общения с платами.

В этом пакете только то, что держит соединение: WebSocket-сервер, сеанс платы с её
командами в ожидании подтверждения и кодек кадров. Ни правил дома, ни решений о
том, кому принадлежит плата, здесь нет — они в прикладном слое.

``protocol``
    кадры wire-протокола как проверенные модели Pydantic.
``wire``
    перевод кадра в значения прикладного слоя и обратно.
``session``
    сеанс одной платы, её команды в ожидании подтверждения и реестр плат.
``connection``
    WebSocket-сервер, к которому дозваниваются платы, и дверь к их командам.
``announcement``
    отложенное объявление платы, развязывающее круг транспорта и её жизненного цикла.
``adapters``
    фасад, с которым говорит прикладной слой.

Транспорт получает всё нужное через конструктор: приёмник сообщений, допуск платы и
её разбор. После сборки ничего не подвязывается, поэтому сеанс платы полностью
описывается её аргументами, и тест собирает его без сокета.
"""

from backend.infrastructure.esp.adapters import BoardGatewayAdapter
from backend.infrastructure.esp.connection import EspConnection
from backend.infrastructure.esp.protocol import (
    PROTOCOL_VERSION,
    AckFrame,
    ClaimedFrame,
    ClaimFrame,
    ErrorFrame,
    GetStateFrame,
    HelloFrame,
    MalformedFrameError,
    OutboundFrame,
    RejectedFrame,
    SensorDataFrame,
    SetRelayFrame,
    StateFrame,
    parse_inbound,
)
from backend.infrastructure.esp.session import BoardRegistry, BoardSession
from backend.infrastructure.esp.wire import read_greeting, read_message

__all__ = [
    "PROTOCOL_VERSION",
    "AckFrame",
    "BoardGatewayAdapter",
    "BoardRegistry",
    "BoardSession",
    "ClaimFrame",
    "ClaimedFrame",
    "ErrorFrame",
    "EspConnection",
    "GetStateFrame",
    "HelloFrame",
    "MalformedFrameError",
    "OutboundFrame",
    "RejectedFrame",
    "SensorDataFrame",
    "SetRelayFrame",
    "StateFrame",
    "parse_inbound",
    "read_greeting",
    "read_message",
]
