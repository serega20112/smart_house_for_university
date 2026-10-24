"""Шина команд платам работает поверх настоящего Redis, а не только фейка.

P0-2 держится на асинхронном pub/sub между процессами, и `fakeredis` это лишь
приближение. Этот тест идёт к настоящей Redis (если поднята) и проверяет то, что решает
судьбу автоматики и сценариев: команда, опубликованная «рабочим», доходит до «сервера
плат» и получает ответ — через реальный канал, без потоков и без блокировок.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress

import pytest
from redis.asyncio import Redis

from backend.application.dto.boards.board_command_result import BoardCommandResult
from backend.config.settings import Settings
from backend.domain.identifiers import EspDeviceId, UserId
from backend.infrastructure.brokers.command_bus import (
    SET_RELAY,
    BoardCommand,
    RedisBoardCommandBus,
)
from tests.conftest import OWNER_UUID

PREFIX = "test-live"


def _make_bus(redis: Redis) -> RedisBoardCommandBus:
    """Строит шину поверх готового соединения.

    Args:
        redis: Асинхронное соединение Redis.

    Returns:
        RedisBoardCommandBus: Шина с коротким ожиданием ответа.
    """
    return RedisBoardCommandBus(redis, PREFIX, 2.0)


async def test_relay_command_round_trips_through_real_redis() -> None:
    """Команда переключения проходит живой канал и получает подтверждение.

    Returns:
        None: Только проверка сквозного прохода через настоящую Redis.
    """
    settings = Settings()
    probe = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await probe.ping()
    except Exception as error:
        await probe.aclose()
        pytest.skip(f"Redis not reachable for live bus test: {error}")
    await probe.aclose()

    api_redis = Redis.from_url(settings.redis_url, decode_responses=True)
    worker_redis = Redis.from_url(settings.redis_url, decode_responses=True)
    api_bus = _make_bus(api_redis)
    worker_bus = _make_bus(worker_redis)
    command = BoardCommand(
        command_id="live-1",
        user_id=UserId.parse(OWNER_UUID),
        board_id=EspDeviceId.generate(),
        kind=SET_RELAY,
        channel=4,
        energized=True,
    )

    async def serve() -> None:
        """Исполняет команды как сервер плат, отвечая подтверждением."""
        async for received in api_bus.commands():
            await api_bus.publish_result(received.command_id, BoardCommandResult(accepted=True))

    task = asyncio.create_task(serve())
    await asyncio.sleep(0.2)
    try:
        result = await worker_bus.execute(command)
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        await api_redis.aclose()
        await worker_redis.aclose()

    assert result.accepted is True
    assert result.reason is None
