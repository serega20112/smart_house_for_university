"""Durable home of the volatile state of the physical layer.

The state of a home outlives the process that observed it. A restart must not
make every board look offline, and several workers have to agree on what the
relays are doing, which is why the state lives in Redis rather than in a
dictionary of a running process.

Every operation of the store is a domain statement applied atomically on the
Redis side: the stories "a board reported positions", "a command was confirmed"
and "a device stopped existing" are each a single script, so two workers never
read a state, change an object and write one back whole. The whole state of one
home is one Redis hash; the manual override window is a separate key with a
native expiry rather than a stored timestamp every reader has to compare
against the clock.
"""

import json
from datetime import datetime
from typing import Final

from redis.asyncio import Redis

from smart_home.application.ports.services import HomeStateStore
from smart_home.domain.climate.climate_reading import ClimateReading
from smart_home.domain.climate.home_state import HomeState
from smart_home.domain.devices.device import Device
from smart_home.domain.devices.device_status import DeviceStatus
from smart_home.domain.devices.relay_state import RelayState
from smart_home.domain.identifiers import DeviceId, UserId

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

_APPLY_RELAYS_SCRIPT: Final = """\
local stored = cjson.decode(
    redis.call('HGET', KEYS[1], 'relay_states') or '{}')
local moved = {}
for index, energized in ipairs(cjson.decode(ARGV[1])) do
    local next_position = energized and 'ON' or 'OFF'
    local was_energized = stored[tostring(index)] == 'ON'
    if next_position == 'ON' ~= was_energized then
        moved[#moved + 1] = index
    end
    stored[tostring(index)] = next_position
end
redis.call(
    'HSET', KEYS[1], 'relay_states', cjson.encode(stored),
    'changed_at', ARGV[2])
return cjson.encode(moved)
"""

_APPLY_SENSOR_REPORT: Final = """\
local moved = {}
local previous = redis.call('HGET', KEYS[1], 'temperature')
if ARGV[1] ~= '' and (not previous or previous ~= ARGV[1]) then
    moved['temperature'] = ARGV[1]
    redis.call('HSET', KEYS[1], 'temperature', ARGV[1])
end
previous = redis.call('HGET', KEYS[1], 'humidity')
if ARGV[2] ~= '' and (not previous or previous ~= ARGV[2]) then
    moved['humidity'] = ARGV[2]
    redis.call('HSET', KEYS[1], 'humidity', ARGV[2])
end
if ARGV[3] ~= '' then
    redis.call('HSET', KEYS[1], 'changed_at', ARGV[3])
end
return cjson.encode(moved)
"""

_RECORD_BOARD_REACHABILITY: Final = """\
local previous = redis.call('HGET', KEYS[1], 'board_online')
local was_online = previous == '1'
if ARGV[1] == '1' then
    redis.call('HSET', KEYS[1], 'board_online', '1')
else
    redis.call('HSET', KEYS[1], 'board_online', '0', 'device_modes', '{}')
end
redis.call('HSET', KEYS[1], 'changed_at', ARGV[2])
return was_online and '1' or '0'
"""

_RECORD_COMMAND_RESULT: Final = """\
local stored = cjson.decode(
    redis.call('HGET', KEYS[1], 'relay_states') or '{}')
stored[ARGV[1]] = ARGV[2]
redis.call('HSET', KEYS[1], 'relay_states', cjson.encode(stored))
local modes = cjson.decode(
    redis.call('HGET', KEYS[1], 'device_modes') or '{}')
modes[ARGV[3]] = ARGV[4]
redis.call(
    'HSET', KEYS[1], 'device_modes', cjson.encode(modes),
    'changed_at', ARGV[5])
"""

_FORGET_DEVICE_STATUS: Final = """\
local modes = cjson.decode(
    redis.call('HGET', KEYS[1], 'device_modes') or '{}')
modes[ARGV[1]] = nil
redis.call('HSET', KEYS[1], 'device_modes', cjson.encode(modes))
"""


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

    async def read(self, user_id: UserId) -> HomeState:
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

    async def record_background_reading(
        self, user_id: UserId, reading: ClimateReading, changed_at: datetime
    ) -> ClimateReading:
        """Apply a sensor report the board produced.

        Args:
            user_id: Owner of the home.
            reading: Measured values, absent where the sensor did not answer.
            changed_at: Moment the board reported them.

        Returns:
            ClimateReading: The values that actually moved.
        """
        moves = json.loads(
            await self._eval(
                _APPLY_SENSOR_REPORT,
                user_id,
                repr(reading.temperature.celsius) if reading.temperature is not None else "",
                repr(reading.humidity.percent) if reading.humidity is not None else "",
                changed_at.isoformat(),
            )
        )
        if not isinstance(moves, dict):
            moves = {}
        return ClimateReading.measured(
            float(moves["temperature"]) if "temperature" in moves else None,
            float(moves["humidity"]) if "humidity" in moves else None,
        )

    async def record_relay_report(
        self, user_id: UserId, states: list[bool], changed_at: datetime
    ) -> tuple[int, ...]:
        """Apply the relay positions reported by a board.

        Args:
            user_id: Owner of the board.
            states: Contact positions ordered by channel, starting at one.
            changed_at: Moment the board reported them.

        Returns:
            tuple[int, ...]: Channels whose position actually moved.
        """
        moved: list[int] = json.loads(
            await self._eval(
                _APPLY_RELAYS_SCRIPT,
                user_id,
                json.dumps([bool(state) for state in states]),
                changed_at.isoformat(),
            )
        )
        return tuple(moved)

    async def record_board_online(
        self, user_id: UserId, online: bool, changed_at: datetime
    ) -> bool:
        """Record whether a board is reachable.

        Args:
            user_id: Owner of the board.
            online: True when the board answered, False when it went away.
            changed_at: Moment of the transition.

        Returns:
            bool: The reachable flag as it stood before the change.
        """
        previous = await self._eval(
            _RECORD_BOARD_REACHABILITY,
            user_id,
            VALUE_TRUE if online else VALUE_FALSE,
            changed_at.isoformat(),
        )
        return _as_text(previous) == VALUE_TRUE

    async def record_command_result(
        self,
        user_id: UserId,
        device: Device,
        status: DeviceStatus,
        changed_at: datetime,
    ) -> None:
        """Store a command result the board confirmed.

        Args:
            user_id: Owner of the device.
            device: Device the command was performed on.
            status: State the device was driven into.
            changed_at: Moment of the confirmation.

        Returns:
            None.
        """
        if device.channel is None:
            return
        await self._eval(
            _RECORD_COMMAND_RESULT,
            user_id,
            str(int(device.channel)),
            RelayState.ON.value if status.is_active else RelayState.OFF.value,
            str(device.id),
            status.value,
            changed_at.isoformat(),
        )

    async def forget_device_status(self, user_id: UserId, device_id: DeviceId) -> None:
        """Drop everything remembered about a device that no longer exists.

        Args:
            user_id: Owner of the removed device.
            device_id: Identifier of the removed device.

        Returns:
            None.
        """
        await self._eval(_FORGET_DEVICE_STATUS, user_id, str(device_id))

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

    async def _eval(self, script: str, user_id: UserId, *args: str | int) -> object:
        return await self._redis.eval(script, 1, self._state_key(user_id), *args)

    def _state_key(self, user_id: UserId) -> str:
        return f"{self._prefix}:state:{user_id}"

    def _override_key(self, user_id: UserId) -> str:
        return f"{self._prefix}:{OVERRIDE_KEY}:{user_id}"


def _decode(user_id: UserId, stored: dict, override: str | None) -> HomeState:
    fields = {_as_text(key): _as_text(value) for key, value in (stored or {}).items()}
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


def _as_text(raw: bytes | str | None) -> str | None:
    if raw is None:
        return None
    return raw.decode("utf-8") if isinstance(raw, bytes) else raw


def _loads(raw: str | bytes | None, fallback: dict[str, str]) -> dict[str, str]:
    if not raw:
        return fallback
    decoded = json.loads(_as_text(raw) or "")
    return decoded if isinstance(decoded, dict) else fallback


def _as_float(raw: str | None) -> float | None:
    return None if raw is None else float(raw)


def _as_datetime(raw: str | None) -> datetime | None:
    return None if raw is None else datetime.fromisoformat(raw)
