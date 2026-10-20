"""Asking a remote model first and falling back to the local pipeline.

When the deployment runs a speech service of its own, that service already holds
the models a transcribed sentence needs. Chaining it is therefore a composition
concern, not a rule of any service: :class:`RemoteFirstUnderstanding` wraps a
remote client and a local port and asks the remote one first.

Only the two outcomes a remote model can legitimately produce are handled: an
answer, or a statement that it is unavailable. Anything else is a bug and keeps
propagating instead of being turned into a silent downgrade.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from smart_home.application.ports.language import (
    CommandUnderstanding,
    CommandUnderstandingPort,
    Intent,
)
from smart_home.domain.climate.temperature import Temperature
from smart_home.domain.devices.capability import Capability
from smart_home.domain.devices.device_kind import DeviceKind
from smart_home.infrastructure.logging import get_logger

log = get_logger("nlp.remote")

UNDERSTAND_PATH = "/understand"


class RemoteUnderstandingUnavailable(RuntimeError):
    """The remote model could not answer.

    Args:
        reason: Machine readable reason.

    Returns:
        None.
    """

    def __init__(self, reason: str) -> None:
        """Initialize the failure.

        Args:
            reason: Machine readable reason.

        Returns:
            None.
        """
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class RemoteAnswer:
    """One structured command as the remote model reported it.

    Args:
        intent: Intent name or None when the sentence is not a command.
        confidence: How sure the remote model is.
        device_name: Device name fragment found in the sentence.
        device_kinds: Device kinds the sentence could be about.
        capability: Capability the sentence asks for.
        temperature: Requested temperature, or None.
        humidity: Requested humidity, or None.
        delay_minutes: Requested delay, or None.
        target: Requested area, or None.

    Returns:
        None.
    """

    intent: str | None
    confidence: float
    device_name: str | None = None
    device_kinds: tuple[str, ...] = ()
    capability: str | None = None
    temperature: float | None = None
    humidity: float | None = None
    delay_minutes: int | None = None
    target: str | None = None


class RemoteUnderstandingClient:
    """Asks the machine that runs the models what a sentence means.

    Args:
        client: Connection to the model host.
        base_url: Address of the model host.
        timeout_sec: Timeout of a single request in seconds.

    Returns:
        None.
    """

    def __init__(self, client: httpx.AsyncClient, base_url: str, timeout_sec: float) -> None:
        """Initialize the client.

        Args:
            client: Connection to the model host.
            base_url: Address of the model host.
            timeout_sec: Timeout of a single request in seconds.

        Returns:
            None.
        """
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_sec

    async def ask(self, text: str) -> RemoteAnswer | None:
        """Ask the remote model to understand a sentence.

        Args:
            text: Text produced by the recognizer.

        Returns:
            RemoteAnswer | None: Structured command, or None when the sentence
            does not describe a command at all.

        Raises:
            RemoteUnderstandingUnavailable: When the remote model cannot answer.
        """
        try:
            response = await self._client.post(
                f"{self._base_url}{UNDERSTAND_PATH}", json={"text": text}, timeout=self._timeout
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise RemoteUnderstandingUnavailable(type(error).__name__) from error
        if not isinstance(payload, dict):
            raise RemoteUnderstandingUnavailable("answer_is_not_an_object")
        return _answer_of(payload)


class RemoteFirstUnderstanding(CommandUnderstandingPort):
    """Asks the remote model first and the local pipeline second.

    Args:
        remote: Client of the machine that runs the models, or None when the
            deployment does not have one.
        local: Pipeline used whenever the remote model has no answer.

    Returns:
        None.
    """

    def __init__(
        self, remote: RemoteUnderstandingClient | None, local: CommandUnderstandingPort
    ) -> None:
        """Initialize the composite.

        Args:
            remote: Client of the machine that runs the models, or None when the
                deployment does not have one.
            local: Pipeline used whenever the remote model has no answer.

        Returns:
            None.
        """
        self._remote = remote
        self._local = local

    async def understand(self, text: str) -> CommandUnderstanding:
        """Interpret a sentence.

        Args:
            text: Raw sentence as typed or as transcribed.

        Returns:
            CommandUnderstanding: What the pipeline made of it.
        """
        answer = await self._remote_answer(text)
        if answer is None:
            return await self._local.understand(text)
        return understanding_of(answer)

    async def is_confident_enough(self, understanding: CommandUnderstanding) -> bool:
        """Return whether an understanding may be carried out.

        Args:
            understanding: Result of the pipeline.

        Returns:
            bool: True when the command may proceed.
        """
        return await self._local.is_confident_enough(understanding)

    async def _remote_answer(self, text: str) -> RemoteAnswer | None:
        if self._remote is None:
            return None
        try:
            return await self._remote.ask(text)
        except RemoteUnderstandingUnavailable as unavailable:
            log.info("nlp.remote_unavailable", reason=unavailable.reason)
            return None


def _answer_of(payload: dict[str, object]) -> RemoteAnswer:
    kinds = payload.get("device_kinds")
    return RemoteAnswer(
        intent=None if payload.get("intent") is None else str(payload["intent"]),
        confidence=_as_float(payload.get("confidence"), 0.0),
        device_name=_as_text(payload.get("device_name")),
        device_kinds=tuple(str(item) for item in kinds) if isinstance(kinds, list) else (),
        capability=_as_text(payload.get("capability")),
        temperature=_as_float(payload.get("temperature"), None),
        humidity=_as_float(payload.get("humidity"), None),
        delay_minutes=_as_int(payload.get("delay_minutes"), None),
        target=_as_text(payload.get("target")),
    )


def understanding_of(answer: RemoteAnswer) -> CommandUnderstanding:
    temperature = answer.temperature
    return CommandUnderstanding(
        intent=Intent.parse(answer.intent),
        device_name=answer.device_name,
        device_kinds=frozenset(_kinds_of(answer.device_kinds)),
        capability=_capability_of(answer.capability),
        temperature=None if temperature is None else Temperature(temperature),
        humidity=answer.humidity,
        delay_minutes=answer.delay_minutes,
        target=answer.target,
        confidence=answer.confidence,
    )


def _kinds_of(names: tuple[str, ...]) -> frozenset[DeviceKind]:
    found: set[DeviceKind] = set()
    for name in names:
        try:
            found.add(DeviceKind.parse(name))
        except ValueError:
            continue
    return frozenset(found)


def _capability_of(name: str | None) -> Capability | None:
    if name is None:
        return None
    try:
        return Capability.parse(name)
    except ValueError:
        return None


def _as_text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _as_float(value: object, default: float | None) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return default
    return float(value)


def _as_int(value: object, default: int | None) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return default
    return int(value)
