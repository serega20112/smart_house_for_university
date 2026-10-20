"""Board communication infrastructure.

``protocol``
    the frames of the wire protocol, as validated Pydantic models.
``onboarding``
    the application operations a handshake raises, kept out of the transport.
``connection``
    the WebSocket server, keyed by account and board.
``adapters``
    the two facades the application talks to.

The connection takes every collaborator it needs as a constructor argument.
Nothing is bound after construction, so a connection is fully described by its
arguments and a test can build one without a socket.
"""

from smart_home.infrastructure.esp.adapters import BoardGatewayAdapter, EspMicrophoneAdapter
from smart_home.infrastructure.esp.connection import (
    BOARD_WEBSOCKET_PATH,
    BoardSession,
    EspConnection,
    MicrophoneStreamForwarder,
    MicrophoneStreamResolver,
)
from smart_home.infrastructure.esp.onboarding import (
    BoardAnnouncement,
    BoardIdentity,
    BoardOnboardingGateway,
)
from smart_home.infrastructure.esp.protocol import (
    AckFrame,
    ArmMicFrame,
    AudioStartFrame,
    AudioStopFrame,
    ClaimedFrame,
    ClaimFrame,
    DisarmMicFrame,
    ErrorFrame,
    GetStateFrame,
    HelloFrame,
    InboundFrame,
    MalformedFrameError,
    MicErrorFrame,
    MicLevelFrame,
    OutboundFrame,
    RejectedFrame,
    SensorDataFrame,
    SetRelayFrame,
    SetVadFrame,
    StateFrame,
    parse_inbound,
)

__all__ = [
    "BOARD_WEBSOCKET_PATH",
    "AckFrame",
    "ArmMicFrame",
    "AudioStartFrame",
    "AudioStopFrame",
    "BoardAnnouncement",
    "BoardGatewayAdapter",
    "BoardIdentity",
    "BoardOnboardingGateway",
    "BoardSession",
    "ClaimFrame",
    "ClaimedFrame",
    "DisarmMicFrame",
    "ErrorFrame",
    "EspConnection",
    "EspMicrophoneAdapter",
    "GetStateFrame",
    "HelloFrame",
    "InboundFrame",
    "MalformedFrameError",
    "MicErrorFrame",
    "MicLevelFrame",
    "MicrophoneStreamForwarder",
    "MicrophoneStreamResolver",
    "OutboundFrame",
    "RejectedFrame",
    "SensorDataFrame",
    "SetRelayFrame",
    "SetVadFrame",
    "StateFrame",
    "parse_inbound",
]
