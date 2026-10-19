"""Durable home of the volatile state of the physical layer.

The state of a home outlives the process that observed it. A restart must not
make every board look offline, and several workers have to agree on what the
relays are doing, which is why the state lives in Redis rather than in a
dictionary of a running process.

The whole state of one home is one Redis hash. Keeping it in a single key means
a save is a single round trip and a load cannot observe half of a change, and it
makes the manual override window a key with a native expiry rather than a stored
timestamp every reader has to compare against the clock.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Final

from redis.asyncio import Redis

from backend.application.ports.services import HomeStateStore
from backend.domain.climate.climate_reading import ClimateReading
from backend.domain.climate.home_state import HomeState
from backend.domain.devices.device_status import DeviceStatus
from backend.domain.devices.relay_state import RelayState
from backend.domain.identifiers import DeviceId, UserId

FIELD_RELAYS: Final = "relay_states"
FIELD_TEMPERATURE: Final = "temperature"
FIELD_HUMIDITY: Final = "humidity"
FIELD_BOARD_ONLINE: Final = "board_online"
FIELD_DEVICE_MODES: Final = "device_modes"
FIELD_CHANGED_AT: Final = "changed_at"

OVERRIDE_KEY: Final = "override_until"
THROTTLE_KEY: Final = "throttle"
VALUE_TRUE: Final = "1"
VALUE_FALSE: Final = "0"


class RedisHomeStateStore(HomeStateStore):
    """Reads and writes the state of a home as a Redis hash.

    Args:
        redis: Connection the state is stored in.
        key_prefix: Namespace every key of this adapter starts with.

    Returns:
        None.
    """

    def __init__(self, redis: Redis, key_prefix: str) -> None:
        """Initialize the store.

        Args:
            redis: Connection the state is stored in.
            key_prefix: Namespace every key of this adapter starts with.

        Returns:
            None.
        """
        self._redis = redis
        self._prefix = key_prefix

    async def load(self, user_id: UserId) -> HomeState:
        """Return the last known state of a home.

        Args:
            user_id: Owner of the home.

        Returns:
            HomeState: Stored state, empty when nothing was ever reported.
        """
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.hgetall(self._state_key(user_id))
            pipe.get(self._override_key(user_id))
            stored, override = await pipe.execute()
        return _decode(user_id, stored, _as_text(override))

    async def save(self, state: HomeState) -> None:
        """Store the current state of a home.

        Args:
            state: State to persist.

        Returns:
            None.
        """
        await self._redis.hset(self._state_key(state.user_id), mapping=_encode(state))

    async def set_override_until(self, user_id: UserId, until: datetime | None) -> None:
        """Set or clear the manual override window of a home.

        The window is a single key with a native expiry, so nobody has to
        subtract minutes from a stored timestamp to find out whether it is over.

        Args:
            user_id: Owner of the home.
            until: Moment the window closes, or None to end it now.

        Returns:
            None.
        """
        key = self._override_key(user_id)
        if until is None:
            await self._redis.delete(key)
            return
        await self._redis.set(key, until.isoformat())
        await self._redis.pexpireat(key, int(until.timestamp() * 1000))

    async def claim_summary_slot(self, user_id: UserId, key: str, window_sec: int) -> bool:
        """Take the right to send a throttled notification.

        The decision is taken by the store itself, which is what keeps two worker
        processes from announcing the same scenario progress at the same moment.

        Args:
            user_id: Owner of the home.
            key: Name of the throttle.
            window_sec: Length of the window in seconds.

        Returns:
            bool: True when this caller took the slot and may send now.
        """
        name = f"{self._prefix}:{THROTTLE_KEY}:{user_id}:{key}"
        return bool(await self._redis.set(name, VALUE_TRUE, ex=max(1, window_sec), nx=True))

    def _state_key(self, user_id: UserId) -> str:
        return f"{self._prefix}:state:{user_id}"

    def _override_key(self, user_id: UserId) -> str:
        return f"{self._prefix}:{OVERRIDE_KEY}:{user_id}"


def _encode(state: HomeState) -> dict[str, str]:
    mapping: dict[str, str] = {
        FIELD_RELAYS: json.dumps(
            {str(channel): item.value for channel, item in state.relay_states.items()},
            separators=(",", ":"),
        ),
        FIELD_BOARD_ONLINE: VALUE_TRUE if state.board_online else VALUE_FALSE,
        FIELD_DEVICE_MODES: json.dumps(
            {str(device): status.value for device, status in state.device_modes.items()},
            separators=(",", ":"),
        ),
    }
    temperature = state.reading.temperature
    if temperature is not None:
        mapping[FIELD_TEMPERATURE] = repr(temperature.celsius)
    humidity = state.reading.humidity
    if humidity is not None:
        mapping[FIELD_HUMIDITY] = repr(humidity.percent)
    if state.changed_at is not None:
        mapping[FIELD_CHANGED_AT] = state.changed_at.isoformat()
    return mapping


def _decode(user_id: UserId, stored: dict[bytes, bytes], override: str | None) -> HomeState:
    fields = {key.decode("utf-8"): value.decode("utf-8") for key, value in stored.items()}
    return HomeState(
        user_id=user_id,
        relay_states={
            int(channel): RelayState(value)
            for channel, value in _loads(fields.get(FIELD_RELAYS), {}).items()
        },
        reading=ClimateReading.measured(
            _as_float(fields.get(FIELD_TEMPERATURE)),
            _as_float(fields.get(FIELD_HUMIDITY)),
        ),
        board_online=fields.get(FIELD_BOARD_ONLINE) == VALUE_TRUE,
        device_modes={
            DeviceId.parse(device): DeviceStatus(status)
            for device, status in _loads(fields.get(FIELD_DEVICE_MODES), {}).items()
        },
        manual_override_until=_as_datetime(override),
        changed_at=_as_datetime(fields.get(FIELD_CHANGED_AT)),
    )


def _as_text(raw: bytes | None) -> str | None:
    return None if raw is None else raw.decode("utf-8")


def _loads(raw: str | None, fallback: dict[str, str]) -> dict[str, str]:
    if not raw:
        return fallback
    decoded = json.loads(raw)
    return decoded if isinstance(decoded, dict) else fallback


def _as_float(raw: str | None) -> float | None:
    return None if raw is None else float(raw)


def _as_datetime(raw: str | None) -> datetime | None:
    return None if raw is None else datetime.fromisoformat(raw)
