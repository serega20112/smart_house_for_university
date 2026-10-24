"""Имена ключей собираются и разбираются в одном модуле.

Формат ключа — договорённость, которая живёт дольше любого читателя: если владельца
вырезает из строки сам потребитель, то смена формата тихо ломает его, а не модуль, где
формат объявлен. Эти проверки держат сборку и разбор рядом.
"""

from __future__ import annotations

import pytest

from backend.domain.identifiers import EspDeviceId, UserId
from backend.infrastructure.brokers import keys
from tests.conftest import OWNER_UUID

PREFIX = "tests"


def test_presence_name_gives_back_the_owner_and_the_board() -> None:
    """Владелец и плата читаются из имени присутствия так же, как записаны."""
    owner = UserId.parse(OWNER_UUID)
    board = EspDeviceId.generate()
    name = keys.board_presence_key(PREFIX, owner, board)

    assert keys.board_presence_owner(name) == owner
    assert keys.board_presence_board(name) == board


def test_a_foreign_key_is_not_read_as_a_presence_name() -> None:
    """Ключ другого вида отвергается, а не разбирается в случайный владелец."""
    name = keys.board_command_channel(PREFIX, UserId.parse(OWNER_UUID))

    with pytest.raises(ValueError):
        keys.board_presence_owner(name)


def test_the_online_index_is_not_a_presence_key_of_some_account() -> None:
    """Список онлайн-аккаунтов не попадает под шаблон присутствия одной платы."""
    owner = UserId.parse(OWNER_UUID)
    index = keys.board_presence_index_key(PREFIX)

    assert not index.startswith(keys.board_presence_pattern(PREFIX, owner)[: -len("*")])
