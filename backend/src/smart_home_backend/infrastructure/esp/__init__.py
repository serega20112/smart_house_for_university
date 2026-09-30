"""Board communication infrastructure."""

from smart_home_backend.infrastructure.esp.connection import EspConnection
from smart_home_backend.infrastructure.esp.gateway import EspGatewayAdapter
from smart_home_backend.infrastructure.esp.protocol import (
    InboundType,
    OutboundType,
    build_get_state,
    build_set_relay,
    parse,
)

__all__ = [
    "EspConnection",
    "EspGatewayAdapter",
    "InboundType",
    "OutboundType",
    "build_get_state",
    "build_set_relay",
    "parse",
]
