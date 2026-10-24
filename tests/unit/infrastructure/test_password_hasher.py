"""Формат хранимого пароля зафиксирован: старые строки обязаны переживать смену стоимости.

Хешер PBKDF2 записывает в строку имя алгоритма, число витков и соль, поэтому повышение
итераций в конфигурации не трогает уже сохранённые пароли — каждая строка проверяется по
вписанной в неё стоимости. Эти проверки сторожат именно совместимость формата: случайный
переход на другой дайджест или иной разделитель сделал бы прежние строки непроверяемыми
молча, а это разлогинило бы весь дом.

Отдельно сторожатся три свойства проверки: она не бросает на испорченной строке, не
считает ключ по стоимости из испорченной строки и не считает его на цикле событий.
Первое и второе — потому что одна обрезанная строка не должна закрывать вход всему
сервису, третье — потому что вход одного человека не должен останавливать кадры плат.
"""

from __future__ import annotations

import asyncio
import threading
import time

import pytest

from backend.infrastructure.security import password_hasher as module
from backend.infrastructure.security.password_hasher import (
    ALGORITHM_PREFIX,
    DEFAULT_DIGEST,
    Pbkdf2PasswordHasher,
)


async def test_hash_is_self_describing_and_verifies():
    """Сохранённая форма называет алгоритм и стоимость и проверяется на месте.

    Returns:
        None: Только проверка формата и сверки.
    """
    hasher = Pbkdf2PasswordHasher(iterations=1234, salt_bytes=16)

    stored = await hasher.hash("correct horse")

    algorithm, recorded_iterations, salt, digest = stored.split("$")
    assert algorithm == f"{ALGORITHM_PREFIX}_{DEFAULT_DIGEST}"
    assert recorded_iterations == "1234"
    assert salt and digest
    assert await hasher.verify("correct horse", stored) is True
    assert await hasher.verify("wrong horse", stored) is False


async def test_a_row_written_at_old_cost_still_verifies_after_cost_rises():
    """Строка, записанная с дешёвой стоимостью, проверяется и у дорогого хешера.

    Returns:
        None: Только проверка совместимости по вписанной в строку стоимости.
    """
    cheap = Pbkdf2PasswordHasher(iterations=100, salt_bytes=16)
    expensive = Pbkdf2PasswordHasher(iterations=600000, salt_bytes=16)

    stored = await cheap.hash("reuse me")

    assert await expensive.verify("reuse me", stored) is True


async def test_foreign_algorithm_form_is_rejected_not_guessed():
    """Форму чужого алгоритма хешер отвергает, а не разбирает снисходительно.

    Returns:
        None: Только проверка отказа.
    """
    hasher = Pbkdf2PasswordHasher(iterations=100, salt_bytes=16)

    assert await hasher.verify("x", "bcrypt$1$salt$digest") is False


@pytest.mark.parametrize(
    "stored",
    [
        "",
        "nonsense",
        "pbkdf2_sha256$not-a-number$c2FsdA$ZGl2",
        "pbkdf2_sha256$100$***$***",
        "pbkdf2_sha256$100$c2FsdA",
    ],
)
async def test_an_unreadable_row_is_refused_instead_of_raising(stored: str):
    """Нечитаемая строка — это отказ, а не исключение из входа.

    Args:
        stored: Хранимая форма, которую невозможно разобрать.

    Returns:
        None: Только проверка отказа.
    """
    hasher = Pbkdf2PasswordHasher(iterations=100, salt_bytes=16)

    assert await hasher.verify("x", stored) is False


async def test_a_row_asking_for_an_enormous_cost_is_refused_before_it_is_computed():
    """Стоимость из испорченной строки не исполняется: ответ приходит отказом сразу.

    Returns:
        None: Только проверка отказа.
    """
    hasher = Pbkdf2PasswordHasher(iterations=100, salt_bytes=16)
    broken = "$".join((f"{ALGORITHM_PREFIX}_{DEFAULT_DIGEST}", str(10**9), "c2FsdA", "ZGl2"))

    assert await hasher.verify("x", broken) is False


async def test_a_missing_record_costs_as_much_as_a_real_check(monkeypatch):
    """Проверка без записи считает ключ с той же стоимостью, что и настоящая.

    Returns:
        None: Только проверка стоимости, с которой посчитан ключ.
    """
    hasher = Pbkdf2PasswordHasher(iterations=100, salt_bytes=16)
    spent = _record_derivations(monkeypatch)

    assert await hasher.verify("nobody", None) is False
    assert spent == [100]


async def test_the_key_is_derived_off_the_event_loop_thread(monkeypatch):
    """Ни хеширование, ни сверка не считаются там, где крутится цикл событий.

    Returns:
        None: Только проверка потока, в котором посчитан ключ.
    """
    hasher = Pbkdf2PasswordHasher(iterations=100, salt_bytes=16)
    stored = await hasher.hash("off the loop")
    loop_thread = threading.get_ident()
    threads: list[int] = []
    original = module.hashlib.pbkdf2_hmac

    def deriving(
        digest_name: str,
        password: bytes,
        salt: bytes,
        iterations: int,
        dklen: int | None = None,
    ) -> bytes:
        threads.append(threading.get_ident())
        return original(digest_name, password, salt, iterations, dklen)

    monkeypatch.setattr(module.hashlib, "pbkdf2_hmac", deriving)

    assert await hasher.verify("off the loop", stored) is True
    assert threads
    assert all(ident != loop_thread for ident in threads)


async def test_ten_simultaneous_logins_do_not_stop_the_loop(monkeypatch):
    """Пока десять паролей считаются, цикл событий продолжает идти.

    Сверка каждого пароля длится 50 мс, а тикер просыпается раз в 10 мс: если бы
    ключ считался на цикле, тикер не проснулся бы ни разу.

    Returns:
        None: Только проверка, что цикл успел тикнуть, пока шла сверка.
    """
    hasher = Pbkdf2PasswordHasher(iterations=100, salt_bytes=16)
    stored = await hasher.hash("one for many")
    original = module.hashlib.pbkdf2_hmac

    def slow(
        digest_name: str,
        password: bytes,
        salt: bytes,
        iterations: int,
        dklen: int | None = None,
    ) -> bytes:
        time.sleep(0.05)
        return original(digest_name, password, salt, iterations, dklen)

    monkeypatch.setattr(module.hashlib, "pbkdf2_hmac", slow)
    ticks = 0

    async def ticking() -> None:
        nonlocal ticks
        while True:
            await asyncio.sleep(0.01)
            ticks += 1

    ticker = asyncio.create_task(ticking())
    results = await asyncio.gather(*(hasher.verify("one for many", stored) for _ in range(10)))
    ticker.cancel()

    assert all(results)
    assert ticks >= 2


def _record_derivations(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Подменяет вывод ключа записью стоимости каждого вызова.

    Args:
        monkeypatch: Подмены текущего теста.

    Returns:
        list[int]: Список, который заполняется стоимостью каждого вывода ключа.
    """
    spent: list[int] = []
    original = module.hashlib.pbkdf2_hmac

    def deriving(
        digest_name: str,
        password: bytes,
        salt: bytes,
        iterations: int,
        dklen: int | None = None,
    ) -> bytes:
        spent.append(iterations)
        return original(digest_name, password, salt, iterations, dklen)

    monkeypatch.setattr(module.hashlib, "pbkdf2_hmac", deriving)
    return spent
