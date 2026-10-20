"""Wire protocol spoken between the backend and the board.

Every frame is a Pydantic model, on both sides of the socket. The inbound frames
form a discriminated union, so a frame that is malformed, truncated or written
by a firmware that says something the server never agreed on is rejected with a
validation error naming the field that broke, instead of being turned into a bag
of optional ``None`` values the rest of the system has to defend against.

Version 3 aligns the backend with the firmware and the protocol documentation:
the board announces its version in ``HELLO`` and a server that cannot agree on
it rejects the board instead of guessing.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

PROTOCOL_VERSION = 3
"""Version both firmware releases and the protocol documentation describe."""

AUDIO_FORMAT_PCM_S16LE = "pcm_s16le"

DEFAULT_SAMPLE_RATE = 4000
"""Rate the analog converter of the board can actually deliver.

An analogRead takes about 100 microseconds on this chip and, with the Wi-Fi
interrupts on top of that, four kilohertz is what the loop keeps up with.
"""
DEFAULT_MAX_MIC_SEC = 15
MIN_THRESHOLD = 0
MAX_THRESHOLD = 1023


class MalformedFrameError(ValueError):
    """A frame of the wire protocol could not be read.

    Args:
        message: What the validation refused.

    Returns:
        None.
    """

    def __init__(self, message: str) -> None:
        """Initialize the failure.

        Args:
            message: What the validation refused.

        Returns:
            None.
        """
        super().__init__(f"malformed board frame: {message}")


class _Inbound(BaseModel):
    """Common behaviour of every frame received from a board."""

    model_config = ConfigDict(extra="allow", populate_by_name=True, frozen=True)


class HelloFrame(_Inbound):
    """The handshake of a board that just dialed in.

    Args:
        type: Discriminator of the union.
        pairing_key: Secret the board presents, absent on a reconnected board
            that already knows its owner.
        label: Short code the board reported about itself.
        mic: Whether the board carries a microphone.
        firmware: Version string the board reported.
        ssid: Name of the network the board is on, absent when it is not on one.
        provisioned: Whether the board already has a network of its own.

    Returns:
        None.
    """

    type: Literal["HELLO"] = "HELLO"
    pairing_key: str | None = None
    label: str = ""
    mic: bool = False
    firmware: str = ""
    ssid: str | None = None
    provisioned: bool = False


class StateFrame(_Inbound):
    """Everything the board knows: contacts and sensors.

    Args:
        type: Discriminator of the union.
        relays: Contact positions ordered by channel, starting at one.
        temperature: Measured temperature, absent when the sensor did not answer.
        humidity: Measured relative humidity, absent when the sensor did not
            answer.

    Returns:
        None.
    """

    type: Literal["STATE"] = "STATE"
    relays: list[bool] = Field(default_factory=list)
    temperature: float | None = None
    humidity: float | None = None


class SensorDataFrame(_Inbound):
    """A reading of the climate sensors alone.

    Args:
        type: Discriminator of the union.
        temperature: Measured temperature, absent when the sensor did not answer.
        humidity: Measured relative humidity, absent when the sensor did not
            answer.

    Returns:
        None.
    """

    type: Literal["SENSOR_DATA"] = "SENSOR_DATA"
    temperature: float | None = None
    humidity: float | None = None


class AckFrame(_Inbound):
    """The confirmation of one command.

    Args:
        type: Discriminator of the union.
        command_id: Identifier of the acknowledged command.

    Returns:
        None.
    """

    type: Literal["ACK"] = "ACK"
    command_id: str


class ErrorFrame(_Inbound):
    """A failure the board reports about itself.

    Args:
        type: Discriminator of the union.
        code: Machine readable error code.
        message: Human readable error description.

    Returns:
        None.
    """

    type: Literal["ERROR"] = "ERROR"
    code: str
    message: str = ""


class MicErrorFrame(ErrorFrame):
    """A failure of the microphone of a board.

    Args:
        type: Discriminator of the union.
        code: Machine readable error code.
        message: Human readable error description.

    Returns:
        None.
    """

    type: Literal["MIC_ERROR"] = "MIC_ERROR"


class AudioStartFrame(_Inbound):
    """The board opened its recording window.

    Args:
        type: Discriminator of the union.
        sample_rate: Samples per second the board streams with.

    Returns:
        None.
    """

    type: Literal["AUDIO_START"] = "AUDIO_START"
    sample_rate: int = Field(default=DEFAULT_SAMPLE_RATE, ge=1)


class AudioStopFrame(_Inbound):
    """The board closed its recording window.

    Args:
        type: Discriminator of the union.
        reason: Why the board stopped.

    Returns:
        None.
    """

    type: Literal["AUDIO_STOP"] = "AUDIO_STOP"
    reason: str = "stopped"


class MicLevelFrame(_Inbound):
    """How loud the microphone of a board hears the room.

    Args:
        type: Discriminator of the union.
        rms: Loudness within the ten bit range of the board converter.
        threshold: Loudness above which the board considers it speech.

    Returns:
        None.
    """

    type: Literal["MIC_LEVEL"] = "MIC_LEVEL"
    rms: int = Field(default=0, ge=0, le=MAX_THRESHOLD)
    threshold: int | None = Field(default=None, ge=MIN_THRESHOLD, le=MAX_THRESHOLD)


type InboundFrame = Annotated[
    HelloFrame
    | StateFrame
    | SensorDataFrame
    | AckFrame
    | ErrorFrame
    | MicErrorFrame
    | AudioStartFrame
    | AudioStopFrame
    | MicLevelFrame,
    Field(discriminator="type"),
]

INBOUND_ADAPTER: TypeAdapter[InboundFrame] = TypeAdapter(InboundFrame)


class OutboundFrame(BaseModel):
    """Common behaviour of every frame sent to a board."""

    model_config = ConfigDict(frozen=True)

    def to_json(self) -> str:
        """Serialize the frame.

        Returns:
            str: JSON document written to the socket.
        """
        return self.model_dump_json()


class SetRelayFrame(OutboundFrame):
    """Switch one relay contact.

    Args:
        type: Frame type.
        command_id: Identifier matched against the acknowledgement.
        channel: Physical relay channel, starting at one.
        state: True closes the contact, False releases it.

    Returns:
        None.
    """

    type: Literal["SET_RELAY"] = "SET_RELAY"
    command_id: str
    channel: int = Field(ge=1)
    state: bool


class GetStateFrame(OutboundFrame):
    """Ask the board to resend everything it knows.

    Args:
        type: Frame type.

    Returns:
        None.
    """

    type: Literal["GET_STATE"] = "GET_STATE"


class ArmMicFrame(OutboundFrame):
    """Open the recording window of a board.

    A window is always finite: a board that forgets to stop cannot flood the
    server.

    Args:
        type: Frame type.
        sample_rate: Samples per second the board should use.
        format: Encoding of the samples.
        max_ms: Longest phrase the board may send.

    Returns:
        None.
    """

    type: Literal["ARM_MIC"] = "ARM_MIC"
    sample_rate: int = Field(ge=1)
    format: str = AUDIO_FORMAT_PCM_S16LE
    max_ms: int = Field(ge=1)


class DisarmMicFrame(OutboundFrame):
    """Close the recording window of a board.

    Args:
        type: Frame type.

    Returns:
        None.
    """

    type: Literal["DISARM_MIC"] = "DISARM_MIC"


class SetVadFrame(OutboundFrame):
    """Change the loudness above which a board sees speech.

    Args:
        type: Frame type.
        threshold: Threshold within the ten bit range of the board converter.

    Returns:
        None.
    """

    type: Literal["SET_VAD"] = "SET_VAD"
    threshold: int = Field(ge=MIN_THRESHOLD, le=MAX_THRESHOLD)


class ClaimFrame(OutboundFrame):
    """Tell a board nobody owns yet that it was understood.

    The account is chosen in the interface of whoever holds the board, so the
    board is not told by whom.

    Args:
        type: Frame type.
        label: Short code the interface shows next to the board.
        ttl_sec: How long the offer stays valid.

    Returns:
        None.
    """

    type: Literal["CLAIM"] = "CLAIM"
    label: str
    ttl_sec: int = Field(ge=1)


class ClaimedFrame(OutboundFrame):
    """Tell a board that it belongs to an account.

    It is sent on every successful handshake on purpose: a board that missed the
    moment of the takeover still learns about it, and being told twice costs
    nothing.

    Args:
        type: Frame type.

    Returns:
        None.
    """

    type: Literal["CLAIMED"] = "CLAIMED"


class RejectedFrame(OutboundFrame):
    """Refuse a board that is not allowed in.

    Args:
        type: Frame type.
        reason: Machine readable reason of the refusal.

    Returns:
        None.
    """

    type: Literal["REJECTED"] = "REJECTED"
    reason: str


class SetNetworkFrame(OutboundFrame):
    """Tell a board which network it is to use.

    The board writes the settings into its own flash and reconnects, so the
    change survives a power cycle. The password travels in this frame only: it
    is never stored on the server and never leaves it again.

    Args:
        type: Frame type.
        command_id: Identifier matched against the acknowledgement.
        ssid: Name of the wireless network.
        password: Password of that network, empty when the network is open.
        host: Address of the server the board reports to.
        server_port: Port of the ordinary interface of that server.
        socket_port: Port of the board socket of that server.
        socket_path: Path of the board socket of that server.

    Returns:
        None.
    """

    type: Literal["SET_NETWORK"] = "SET_NETWORK"
    command_id: str
    ssid: str = Field(min_length=1, max_length=32)
    password: str = Field(default="", max_length=64)
    host: str = Field(min_length=1, max_length=64)
    server_port: int = Field(ge=1, le=65535)
    socket_port: int = Field(ge=1, le=65535)
    socket_path: str = Field(min_length=1, max_length=64)


def parse_inbound(raw: str | bytes) -> InboundFrame:
    """Read one frame received from a board.

    Args:
        raw: Raw frame as it arrived on the socket.

    Returns:
        InboundFrame: Validated frame.

    Raises:
        MalformedFrameError: When the frame is not a valid frame of the
            protocol.
    """
    text = raw.decode("utf-8", "replace") if isinstance(raw, bytes | bytearray) else raw
    try:
        return INBOUND_ADAPTER.validate_json(text)
    except ValueError as error:
        raise MalformedFrameError(str(error)) from error
