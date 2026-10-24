"""Как живое состояние дома лежит в Redis.

Всё состояние одного дома — один хеш, а окно ручного управления — отдельный ключ
с собственным сроком жизни, чтобы читателю не пришлось вычитать минуты из
сохранённой метки времени.

Каждое изменение применяется скриптом на стороне Redis: «плата сообщила
положения», «команда подтверждена», «устройство перестало существовать» — это по
одному атомарному скрипту, поэтому два воркера никогда не прочитают состояние,
не меняя объект, и не запишут его обратно целиком.

Поля хеша и значения перечислений подставляются в Lua из единственного места —
этого модуля, — поэтому словарь железа в скриптах не может разойтись с тем, что
объявлено в домене.
"""

from __future__ import annotations

from typing import Final

from backend.domain.entities.home_state.home_state import HomeState
from backend.domain.identifiers import DeviceId, UserId
from backend.domain.value_objects.climate.climate_reading import ClimateReading
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.domain.value_objects.devices.relay_state import RelayState
from backend.infrastructure.brokers.decoding import as_datetime, as_float, as_text, loads

FIELD_RELAYS: Final = "relay_states"
FIELD_TEMPERATURE: Final = "temperature"
FIELD_HUMIDITY: Final = "humidity"
FIELD_BOARD_ONLINE: Final = "board_online"
FIELD_DEVICE_MODES: Final = "device_modes"
FIELD_CHANGED_AT: Final = "changed_at"

VALUE_TRUE: Final = "1"
VALUE_FALSE: Final = "0"

_TOKENS: Final = {
    "RELAY_STATES": FIELD_RELAYS,
    "TEMPERATURE": FIELD_TEMPERATURE,
    "HUMIDITY": FIELD_HUMIDITY,
    "BOARD_ONLINE": FIELD_BOARD_ONLINE,
    "DEVICE_MODES": FIELD_DEVICE_MODES,
    "CHANGED_AT": FIELD_CHANGED_AT,
    "ON": RelayState.ON.value,
    "OFF": RelayState.OFF.value,
    "TRUE": VALUE_TRUE,
    "FALSE": VALUE_FALSE,
}


def script(text: str) -> str:
    """Подставляет в Lua имена полей и значения перечислений из этого модуля.

    Args:
        text: Исходник скрипта с метками вида ``<RELAY_STATES>``.

    Returns:
        str: Готовый к отправке скрипт.
    """
    resolved = text
    for token, value in _TOKENS.items():
        resolved = resolved.replace(f"<{token}>", value)
    return resolved


APPLY_RELAYS: Final = script(
    """
local stored = cjson.decode(
    redis.call('HGET', KEYS[1], '<RELAY_STATES>') or '{}')
local moved = {}
for index, energized in ipairs(cjson.decode(ARGV[1])) do
    local next_position = energized and '<ON>' or '<OFF>'
    local was_energized = stored[tostring(index)] == '<ON>'
    if (next_position == '<ON>') ~= was_energized then
        moved[#moved + 1] = index
    end
    stored[tostring(index)] = next_position
end
redis.call(
    'HSET', KEYS[1], '<RELAY_STATES>', cjson.encode(stored),
    '<CHANGED_AT>', ARGV[2])
return cjson.encode(moved)
"""
)

APPLY_SENSOR_REPORT: Final = script(
    """
local moved = {}
local previous = redis.call('HGET', KEYS[1], '<TEMPERATURE>')
if ARGV[1] ~= '' and (not previous or previous ~= ARGV[1]) then
    moved['<TEMPERATURE>'] = ARGV[1]
    redis.call('HSET', KEYS[1], '<TEMPERATURE>', ARGV[1])
end
previous = redis.call('HGET', KEYS[1], '<HUMIDITY>')
if ARGV[2] ~= '' and (not previous or previous ~= ARGV[2]) then
    moved['<HUMIDITY>'] = ARGV[2]
    redis.call('HSET', KEYS[1], '<HUMIDITY>', ARGV[2])
end
if ARGV[3] ~= '' then
    redis.call('HSET', KEYS[1], '<CHANGED_AT>', ARGV[3])
end
return cjson.encode(moved)
"""
)

RECORD_BOARD_REACHABILITY: Final = script(
    """
local previous = redis.call('HGET', KEYS[1], '<BOARD_ONLINE>')
local was_online = previous == '<TRUE>'
if ARGV[1] == '<TRUE>' then
    redis.call('HSET', KEYS[1], '<BOARD_ONLINE>', '<TRUE>')
else
    redis.call('HSET', KEYS[1], '<BOARD_ONLINE>', '<FALSE>', '<DEVICE_MODES>', '{}')
end
redis.call('HSET', KEYS[1], '<CHANGED_AT>', ARGV[2])
return was_online and '<TRUE>' or '<FALSE>'
"""
)

RECORD_COMMAND_RESULT: Final = script(
    """
local stored = cjson.decode(
    redis.call('HGET', KEYS[1], '<RELAY_STATES>') or '{}')
stored[ARGV[1]] = ARGV[2]
redis.call('HSET', KEYS[1], '<RELAY_STATES>', cjson.encode(stored))
local modes = cjson.decode(
    redis.call('HGET', KEYS[1], '<DEVICE_MODES>') or '{}')
modes[ARGV[3]] = ARGV[4]
redis.call(
    'HSET', KEYS[1], '<DEVICE_MODES>', cjson.encode(modes),
    '<CHANGED_AT>', ARGV[5])
"""
)

FORGET_DEVICE_STATUS: Final = script(
    """
local modes = cjson.decode(
    redis.call('HGET', KEYS[1], '<DEVICE_MODES>') or '{}')
modes[ARGV[1]] = nil
redis.call('HSET', KEYS[1], '<DEVICE_MODES>', cjson.encode(modes))
"""
)


def home_state_of(user_id: UserId, stored: dict, override: str | None) -> HomeState:
    """Собирает состояние дома из хеша Redis и ключа окна ручного управления.

    Args:
        user_id: Владелец дома.
        stored: Сырой хеш состояния таким, каким его вернул сервер.
        override: Момент закрытия окна ручного управления или None.

    Returns:
        HomeState: Состояние, пустое там, где ничего ещё не сообщали.
    """
    fields = {as_text(key): as_text(value) for key, value in (stored or {}).items()}
    return HomeState(
        user_id=user_id,
        relay_states={
            int(channel): RelayState(value)
            for channel, value in loads(fields.get(FIELD_RELAYS), {}).items()
        },
        reading=ClimateReading.measured(
            as_float(fields.get(FIELD_TEMPERATURE)),
            as_float(fields.get(FIELD_HUMIDITY)),
        ),
        board_online=fields.get(FIELD_BOARD_ONLINE) == VALUE_TRUE,
        device_modes={
            DeviceId.parse(device): DeviceStatus(status)
            for device, status in loads(fields.get(FIELD_DEVICE_MODES), {}).items()
        },
        manual_override_until=as_datetime(override),
        changed_at=as_datetime(fields.get(FIELD_CHANGED_AT)),
    )
