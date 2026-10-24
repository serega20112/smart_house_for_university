"""Шина команд доносит приказ рабочего до сервера плат и возвращает ответ.

Здесь проверяется ровно тот механизм, которого не хватало в P0-2: рабочий публикует
команду в канал аккаунта, сторона сервера плат читает её и отвечает в канал команды, а
отправитель этого ответа дожидается. Настоящий сокет платы не поднимается — вместо него
ответ публикует подставный исполнитель, поэтому проверка отделяет транспорт сообщений
от транспорта железа.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress

from fakeredis import FakeServer, aioredis

from backend.application.dto.boards.board_command_reason import BoardCommandReason
from backend.application.dto.boards.board_command_result import BoardCommandResult
from backend.domain.identifiers import EspDeviceId, UserId
from backend.domain.value_objects.boards.network_profile import NetworkProfile
from backend.infrastructure.brokers.command_bus import (
    SET_NETWORK,
    SET_RELAY,
    BoardCommand,
    RedisBoardCommandBus,
)
from tests.conftest import OWNER_UUID

PREFIX = "tests"
TIMEOUT = 2.0


def make_bus(server: FakeServer) -> RedisBoardCommandBus:
    """Строит шину поверх общего фейкового сервера Redis.

    Args:
        server: Общий сервер, через который соединяются обе стороны.

    Returns:
        RedisBoardCommandBus: Шина на свежном соединении с ответами по тексту.
    """
    redis = aioredis.FakeRedis(server=server, decode_responses=True)
    return RedisBoardCommandBus(redis, PREFIX, TIMEOUT)


def make_profile() -> NetworkProfile:
    """Возвращает любой годный профиль сети для сериализации команды.

    Returns:
        NetworkProfile: Профиль с корректными сетью и адресом сервера.
    """
    return NetworkProfile(
        ssid="home",
        password="wifi-pass-42",
        host="10.0.0.5",
        server_port=8000,
        socket_port=8001,
        socket_path="/ws/board",
    )


async def test_relay_command_round_trip_returns_confirmation():
    """Команда переключения доходит и получает подтверждение от исполнителя.

    Returns:
        None: Только проверка сквозного прохода команды и ответа.
    """
    server = FakeServer()
    worker_bus = make_bus(server)
    api_bus = make_bus(server)
    command = BoardCommand(
        command_id="cmd-1",
        user_id=UserId.parse(OWNER_UUID),
        board_id=EspDeviceId.generate(),
        kind=SET_RELAY,
        channel=3,
        energized=True,
    )

    async def serve() -> None:
        """Исполняет команды как сервер плат, отвечая подтверждением."""
        async for received in api_bus.commands():
            await api_bus.publish_result(received.command_id, BoardCommandResult(accepted=True))

    task = asyncio.create_task(serve())
    await asyncio.sleep(0.1)
    try:
        result = await worker_bus.execute(command)
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    assert result.accepted is True
    assert result.reason is None


async def test_command_times_out_when_nobody_answers():
    """Молчание сервера плат превращается в явный отказ, а не в вечное ожидание.

    Returns:
        None: Только проверка отказа по истечении ожидания.
    """
    server = FakeServer()
    worker_bus = make_bus(server)
    command = BoardCommand(
        command_id="cmd-silent",
        user_id=UserId.parse(OWNER_UUID),
        board_id=EspDeviceId.generate(),
        kind=SET_NETWORK,
        network=BoardCommand.network_of(make_profile()),
    )

    result = await worker_bus.execute(command)

    assert result.accepted is False
    assert result.reason == BoardCommandReason.ACK_TIMEOUT


async def test_network_password_travels_outside_the_channel_and_is_used_once() -> None:
    """Пароль сети не попадает в кадр канала и читается исполнителем один раз.

    Канал общий на аккаунт, его видит каждый, у кого есть доступ к Redis, а пароль
    сети — секрет дома. Поэтому в кадре едет только ссылка на ключ, а сам секрет
    лежит отдельно, с коротким сроком жизни и одним читателем.

    Returns:
        None: Только проверка разделения кадра и секрета.
    """
    server = FakeServer()
    worker_bus = make_bus(server)
    api_bus = make_bus(server)
    profile = make_profile()
    command = BoardCommand(
        command_id="cmd-network",
        user_id=UserId.parse(OWNER_UUID),
        board_id=EspDeviceId.generate(),
        kind=SET_NETWORK,
        network=BoardCommand.network_of(profile),
        secret=profile.password,
    )
    restored: list[str | None] = []

    async def serve() -> None:
        """Исполняет команды как сервер плат, собирая профиль из хранилища."""
        async for received in api_bus.commands():
            assert received.secret is None
            secret = await api_bus.take_secret(received.command_id)
            rebuilt = received.network_profile(secret)
            restored.append(None if rebuilt is None else rebuilt.password)
            await api_bus.publish_result(received.command_id, BoardCommandResult(accepted=True))

    task = asyncio.create_task(serve())
    await asyncio.sleep(0.1)
    try:
        result = await worker_bus.execute(command)
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    assert profile.password not in command.to_json()
    assert result.accepted is True
    assert result.reason is None
    assert restored == [profile.password]
    assert await api_bus.take_secret(command.command_id) is None
