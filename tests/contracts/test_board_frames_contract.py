"""Контракт прошивка ↔ бэкенд сверяется по фикстурам, снятым с прошивки.

Эти проверки ловят рассинхрон договора, который раньше замечали только глазами: каждый
кадр хранится отдельным JSON-файлом ровно в том виде, каким его пишет прошивка, и
парсится тем же `parse_inbound`, что и в бою. Файл лишнего поля и файл чужой версии
протокола обязаны отвергаться — иначе контракт снова стал бы трёхчастным и неисполняемым.
Обновляются фикстуры вместе с прошивкой.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from backend.domain.value_objects.devices.relay_channel import PHYSICAL_RELAY_LIMIT
from backend.infrastructure.esp import protocol

FIXTURES = Path(__file__).parent
FIRMWARE = Path(__file__).resolve().parents[2] / "src" / "firmware" / "src"


def load(name: str) -> str:
    """Читает текст фикстуры кадра.

    Args:
        name: Имя JSON-файла в папке фикстур.

    Returns:
        str: Raw текст кадра так, как передала бы его прошивка.
    """
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_hello_fixture_parses_to_every_declared_field():
    """HELLO прошивки читается целиком, без потерянных полей.

    Returns:
        None: Только проверка разобранных значений.
    """
    frame = protocol.parse_inbound(load("hello.json"))

    assert isinstance(frame, protocol.HelloFrame)
    assert frame.protocol_version == protocol.PROTOCOL_VERSION
    assert frame.firmware_version == "1.4.0"
    assert frame.pairing_key == "9F2C7A11"
    assert frame.label == "9F2C7A"
    assert frame.claim is False
    assert frame.relays == [True, False, False, False, False, False]
    assert frame.ssid == "HomeNet"
    assert frame.provisioned is True
    assert frame.server_host == "192.168.1.10"
    assert frame.server_port == 8000
    assert frame.socket_port == 8001
    assert frame.socket_path == "/ws/board"


def test_state_fixture_parses():
    """STATE с контактами и обоими датчиками читается корректно.

    Returns:
        None: Только проверка разобранных значений.
    """
    frame = protocol.parse_inbound(load("state.json"))

    assert isinstance(frame, protocol.StateFrame)
    assert frame.relays == [False, True, False, False, False, False]
    assert frame.temperature == 21.5
    assert frame.humidity == 44.0


def test_sensor_data_fixture_parses():
    """SENSOR_DATA читается как телеметрия без касания реле.

    Returns:
        None: Только проверка разобранных значений.
    """
    frame = protocol.parse_inbound(load("sensor_data.json"))

    assert isinstance(frame, protocol.SensorDataFrame)
    assert frame.temperature == 22.0
    assert frame.humidity == 47.5


def test_ack_fixture_parses():
    """ACK читается с тем идентификатором команды, что подтверждают.

    Returns:
        None: Только проверка разборанного идентификатора.
    """
    frame = protocol.parse_inbound(load("ack.json"))

    assert isinstance(frame, protocol.AckFrame)
    assert frame.command_id == "9f2c7a-3"


def test_error_fixture_parses():
    """ERROR читается с машинночитаемым кодом и человекочитаемым текстом.

    Returns:
        None: Только проверка разобранных полей.
    """
    frame = protocol.parse_inbound(load("error.json"))

    assert isinstance(frame, protocol.ErrorFrame)
    assert frame.code == "relay_fault"
    assert frame.message == "channel 3 is stuck"


@pytest.mark.parametrize("name", ["hello_wrong_protocol.json", "hello_extra_field.json"])
def test_out_of_contract_hello_is_rejected(name: str) -> None:
    """HELLO чужой версии протокола или с лишним полем не принимается.

    Args:
        name: Имя фикстуры, нарушающей контракт.

    Returns:
        None: Только проверка отказа.
    """
    with pytest.raises(protocol.MalformedFrameError):
        protocol.parse_inbound(load(name))


def _firmware_constant(name: str, header: str) -> int:
    """Вытаскивает целочисленную константу из заголовка прошивки.

    Args:
        name: Имя константы, которую ищут в заголовке.
        header: Имя файла заголовка в папке исходников прошивки.

    Returns:
        int: Значение константы, объявленной прошивкой.

    Raises:
        AssertionError: Когда константа в заголовке не найдена.
    """
    text = (FIRMWARE / header).read_text(encoding="utf-8")
    found = re.search(rf"{name}\s*=\s*(\d+)", text)
    assert found is not None, f"{name} not declared in {header}"
    return int(found.group(1))


def test_backend_and_firmware_declare_one_protocol_version():
    """Бэкенд и прошивка называют одну и ту же версию протокола.

    Returns:
        None: Только сверку двух независимых объявлений одной величины.
    """
    assert _firmware_constant("PROTOCOL_VERSION", "transport.h") == protocol.PROTOCOL_VERSION


def test_hello_fixture_relays_match_firmware_relay_count():
    """Число контактов в HELLO-фикстуре равно числу реле платы и влезает в модель.

    Returns:
        None: Только сверку железа, фикстуры и предела канала.
    """
    relay_count = _firmware_constant("RELAY_COUNT", "relay.h")
    frame = protocol.parse_inbound(load("hello.json"))

    assert isinstance(frame, protocol.HelloFrame)
    assert len(frame.relays) == relay_count
    assert 1 <= relay_count <= PHYSICAL_RELAY_LIMIT


def test_firmware_hello_reports_its_server_endpoint():
    """Прошивка в handshake называет адрес сервера — тот же набор ключей, что читает бэкенд.

    Returns:
        None: Только сверку, что `sendHello` пишет все поля эндпоинта сервера.
    """
    text = (FIRMWARE / "transport.cpp").read_text(encoding="utf-8")

    for key in ("server_host", "server_port", "socket_port", "socket_path"):
        assert f'doc["{key}"]' in text, f"sendHello does not emit {key}"
