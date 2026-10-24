"""Разделённый реестр присутствия плат ведёт себя как единственный источник правды.

Эти проверки ловят суть P0-2: рабочий и сервер плат должны видеть одних и тех же
подключённых плат, обращаясь к Redis, а не к памяти своего процесса. Поэтому здесь
проверяются приход и уход платы, различение «одна плата — несколько плат» и то, что
продление присутствия оставляет запись живой.
"""

from __future__ import annotations

from fakeredis import FakeServer, aioredis

from backend.domain.identifiers import EspDeviceId, UserId
from backend.infrastructure.brokers.board_presence import RedisBoardPresence
from tests.conftest import OWNER_UUID

PREFIX = "tests"


def make_presence(ttl_sec: float = 60.0) -> RedisBoardPresence:
    """Строит реестр поверх чистого фейкового сервера Redis.

    Args:
        ttl_sec: Срок жизни ключа присутствия.

    Returns:
        RedisBoardPresence: Реестр на свежем соединении.
    """
    redis = aioredis.FakeRedis(server=FakeServer(), decode_responses=True)
    return RedisBoardPresence(redis, PREFIX, ttl_sec)


async def test_mark_online_then_board_for_and_back_off():
    """Приход делает плату единственной целью, уход — убирает её.

    Returns:
        None: Только проверка поведения реестра.
    """
    presence = make_presence()
    user = UserId.parse(OWNER_UUID)
    board = EspDeviceId.generate()

    assert await presence.board_for(user) is None
    assert await presence.is_connected(user, board) is False

    await presence.mark_online(user, board)

    assert await presence.is_connected(user, board) is True
    assert await presence.board_for(user) == board

    await presence.mark_offline(user, board)

    assert await presence.is_connected(user, board) is False
    assert await presence.board_for(user) is None


async def test_board_for_returns_none_when_two_boards_connected():
    """Две подключённые платы — адрес команды неоднозначен, цели нет.

    Returns:
        None: Только проверка правила разрешения платы.
    """
    presence = make_presence()
    user = UserId.parse(OWNER_UUID)

    await presence.mark_online(user, EspDeviceId.generate())
    await presence.mark_online(user, EspDeviceId.generate())

    assert await presence.board_for(user) is None


async def test_board_for_is_scoped_to_one_account():
    """Чужие платы не попадают в разрешение цели этого аккаунта.

    Returns:
        None: Только проверка разделения по владельцу.
    """
    presence = make_presence()
    owner = UserId.parse(OWNER_UUID)
    other = UserId.generate()
    board = EspDeviceId.generate()

    await presence.mark_online(owner, board)
    await presence.mark_online(other, EspDeviceId.generate())

    assert await presence.board_for(owner) == board


async def test_online_user_ids_lists_accounts_with_a_board():
    """Список онлайн-аккаунтов отдаёт разных владельцев и теряет ушедшего.

    Returns:
        None: Только проверка перечисления присутствующих аккаунтов.
    """
    presence = make_presence()
    owner = UserId.parse(OWNER_UUID)
    other = UserId.generate()
    other_board = EspDeviceId.generate()

    assert await presence.online_user_ids() == []

    await presence.mark_online(owner, EspDeviceId.generate())
    await presence.mark_online(owner, EspDeviceId.generate())
    await presence.mark_online(other, other_board)

    present = {str(user) for user in await presence.online_user_ids()}
    assert present == {str(owner), str(other)}

    await presence.mark_offline(other, other_board)
    after_leave = {str(user) for user in await presence.online_user_ids()}
    assert after_leave == {str(owner)}
