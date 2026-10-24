"""Как живое состояние дома лежит в Redis.

Всё состояние одного дома — один хеш, а окно ручного управления — отдельный ключ
с собственным сроком жизни, чтобы читателю не пришлось вычитать минуты из
сохранённой метки времени.

Физическое ключуется платой: ``relay_states`` — словарь «плата → каналы»,
``readings`` — словарь «плата → показания», ``online_boards`` — словарь доступных
плат. Дом из двух плат с устройством на первом канале каждой поэтому не склеивает
их в один контакт и не показывает состояние чужого устройства.

Каждое изменение применяется скриптом на стороне Redis: «плата сообщила
положения», «команда подтверждена», «устройство перестало существовать» — это по
одному атомарному скрипту, поэтому два воркера никогда не прочитают состояние,
не меняя объект, и не запишут его обратно целиком.

Форма хеша помечена ``schema_version``. Хеш другой формы — это не состояние, а
мусор: изменяющий скрипт стирает его перед записью, а чтение возвращает пустой дом.
Форма меняется вместе с кодом, а живое состояние платы восстанавливают следующим
сообщением, поэтому сброс дешевле, чем догадки о том, что значили старые поля.

Поля хеша и значения перечислений подставляются в Lua из единственного места —
этого модуля, — поэтому словарь железа в скриптах не может разойтись с тем, что
объявлено в домене.
"""

from __future__ import annotations

from typing import Final

from backend.domain.entities.home_state.home_state import HomeState
from backend.domain.identifiers import DeviceId, EspDeviceId, UserId
from backend.domain.value_objects.climate.climate_reading import ClimateReading
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.domain.value_objects.devices.relay_state import RelayState
from backend.infrastructure.brokers.decoding import as_datetime, as_float, as_text, loads

STATE_VERSION: Final = "2"

FIELD_SCHEMA_VERSION: Final = "schema_version"
FIELD_RELAYS: Final = "relay_states"
FIELD_READINGS: Final = "readings"
FIELD_LAST_READING_BOARD: Final = "last_reading_board"
FIELD_ONLINE_BOARDS: Final = "online_boards"
FIELD_DEVICE_MODES: Final = "device_modes"
FIELD_CHANGED_AT: Final = "changed_at"

VALUE_TRUE: Final = "1"
VALUE_FALSE: Final = "0"

_TOKENS: Final = {
    "SCHEMA_VERSION": FIELD_SCHEMA_VERSION,
    "VERSION": STATE_VERSION,
    "RELAY_STATES": FIELD_RELAYS,
    "READINGS": FIELD_READINGS,
    "LAST_READING_BOARD": FIELD_LAST_READING_BOARD,
    "ONLINE_BOARDS": FIELD_ONLINE_BOARDS,
    "DEVICE_MODES": FIELD_DEVICE_MODES,
    "CHANGED_AT": FIELD_CHANGED_AT,
    "ON": RelayState.ON.value,
    "OFF": RelayState.OFF.value,
    "TRUE": VALUE_TRUE,
    "FALSE": VALUE_FALSE,
}

_RESET_STALE_FORM: Final = """
if redis.call('HGET', KEYS[1], '<SCHEMA_VERSION>') ~= '<VERSION>' then
    redis.call('DEL', KEYS[1])
    redis.call('HSET', KEYS[1], '<SCHEMA_VERSION>', '<VERSION>')
end
"""


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
    _RESET_STALE_FORM
    + """
local boards = cjson.decode(redis.call('HGET', KEYS[1], '<RELAY_STATES>') or '{}')
local stored = boards[ARGV[1]] or {}
local moved = {}
for index, energized in ipairs(cjson.decode(ARGV[2])) do
    local next_position = energized and '<ON>' or '<OFF>'
    local was_energized = stored[tostring(index)] == '<ON>'
    if (next_position == '<ON>') ~= was_energized then
        moved[#moved + 1] = index
    end
    stored[tostring(index)] = next_position
end
boards[ARGV[1]] = stored
redis.call(
    'HSET', KEYS[1], '<RELAY_STATES>', cjson.encode(boards), '<CHANGED_AT>', ARGV[3])
return cjson.encode(moved)
"""
)

APPLY_SENSOR_REPORT: Final = script(
    _RESET_STALE_FORM
    + """
local boards = cjson.decode(redis.call('HGET', KEYS[1], '<READINGS>') or '{}')
local stored = boards[ARGV[1]] or {}
local moved = {}
if ARGV[2] ~= '' and (not stored['temperature'] or stored['temperature'] ~= ARGV[2]) then
    stored['temperature'] = ARGV[2]
    moved['temperature'] = ARGV[2]
end
if ARGV[3] ~= '' and (not stored['humidity'] or stored['humidity'] ~= ARGV[3]) then
    stored['humidity'] = ARGV[3]
    moved['humidity'] = ARGV[3]
end
boards[ARGV[1]] = stored
redis.call(
    'HSET', KEYS[1], '<READINGS>', cjson.encode(boards),
    '<LAST_READING_BOARD>', ARGV[1], '<CHANGED_AT>', ARGV[4])
return cjson.encode(moved)
"""
)

RECORD_BOARD_REACHABILITY: Final = script(
    _RESET_STALE_FORM
    + """
local boards = cjson.decode(redis.call('HGET', KEYS[1], '<ONLINE_BOARDS>') or '{}')
local was_online = boards[ARGV[1]] == '<TRUE>'
if ARGV[2] == '<TRUE>' then
    boards[ARGV[1]] = '<TRUE>'
else
    boards[ARGV[1]] = nil
end
redis.call('HSET', KEYS[1], '<ONLINE_BOARDS>', cjson.encode(boards), '<CHANGED_AT>', ARGV[3])
return was_online and '<TRUE>' or '<FALSE>'
"""
)

RECORD_COMMAND_RESULT: Final = script(
    _RESET_STALE_FORM
    + """
local boards = cjson.decode(redis.call('HGET', KEYS[1], '<RELAY_STATES>') or '{}')
local stored = boards[ARGV[1]] or {}
stored[ARGV[2]] = ARGV[3]
boards[ARGV[1]] = stored
redis.call('HSET', KEYS[1], '<RELAY_STATES>', cjson.encode(boards))
local modes = cjson.decode(
    redis.call('HGET', KEYS[1], '<DEVICE_MODES>') or '{}')
modes[ARGV[4]] = ARGV[5]
redis.call(
    'HSET', KEYS[1], '<DEVICE_MODES>', cjson.encode(modes),
    '<CHANGED_AT>', ARGV[6])
"""
)

FORGET_DEVICE_STATUS: Final = script(
    _RESET_STALE_FORM
    + """
local modes = cjson.decode(
    redis.call('HGET', KEYS[1], '<DEVICE_MODES>') or '{}')
modes[ARGV[1]] = nil
redis.call('HSET', KEYS[1], '<DEVICE_MODES>', cjson.encode(modes))
"""
)


def home_state_of(user_id: UserId, stored: dict, override: str | None) -> HomeState:
    """Собирает состояние дома из хеша Redis и ключа окна ручного управления.

    Хеш без метки текущей формы не разбирается «как получится»: старые поля
    значили другое, и прочитанное из них состояние было бы тихо неверным. Вместо
    догадок возвращается пустой дом — платы наполнят его следующим сообщением.

    Args:
        user_id: Владелец дома.
        stored: Сырой хеш состояния таким, каким его вернул сервер.
        override: Момент закрытия окна ручного управления или None.

    Returns:
        HomeState: Состояние, пустое там, где ничего ещё не сообщали.
    """
    fields = {as_text(key): as_text(value) for key, value in (stored or {}).items()}
    if fields.get(FIELD_SCHEMA_VERSION) != STATE_VERSION:
        return HomeState(user_id=user_id, manual_override_until=as_datetime(override))
    last_reading = fields.get(FIELD_LAST_READING_BOARD)
    return HomeState(
        user_id=user_id,
        relay_states={
            EspDeviceId.parse(board): _channels_of(channels)
            for board, channels in loads(fields.get(FIELD_RELAYS), {}).items()
        },
        readings={
            EspDeviceId.parse(board): _reading_of(values)
            for board, values in loads(fields.get(FIELD_READINGS), {}).items()
        },
        last_reading_board=None if not last_reading else EspDeviceId.parse(last_reading),
        online_boards=frozenset(
            EspDeviceId.parse(board)
            for board, flag in loads(fields.get(FIELD_ONLINE_BOARDS), {}).items()
            if flag == VALUE_TRUE
        ),
        device_modes={
            DeviceId.parse(device): DeviceStatus(status)
            for device, status in loads(fields.get(FIELD_DEVICE_MODES), {}).items()
        },
        manual_override_until=as_datetime(override),
        changed_at=as_datetime(fields.get(FIELD_CHANGED_AT)),
    )


def _channels_of(raw: object) -> dict[int, RelayState]:
    """Разбирает положения каналов одной платы.

    Args:
        raw: Значение из поля хеша, каким его вернул разбор JSON.

    Returns:
        dict[int, RelayState]: Каналы платы; пусто, когда плата ничего не сообщала.
    """
    if not isinstance(raw, dict):
        return {}
    return {int(channel): RelayState(value) for channel, value in raw.items()}


def _reading_of(raw: object) -> ClimateReading:
    """Разбирает показания датчиков одной платы.

    Args:
        raw: Значение из поля хеша, каким его вернул разбор JSON.

    Returns:
        ClimateReading: Показания платы; пусто, когда она ничего не мерила.
    """
    if not isinstance(raw, dict):
        return ClimateReading()
    return ClimateReading.measured(as_float(raw.get("temperature")), as_float(raw.get("humidity")))
