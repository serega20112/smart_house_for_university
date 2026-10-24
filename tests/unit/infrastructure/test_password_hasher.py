"""Формат хранимого пароля зафиксирован: старые строки обязаны переживать смену стоимости.

Хешер PBKDF2 записывает в строку имя алгоритма, число витков и соль, поэтому повышение
итераций в конфигурации не трогает уже сохранённые пароли — каждая строка проверяется по
вписанной в неё стоимости. Эти проверки сторожат именно совместимость формата: случайный
переход на другой дайджест или иной разделитель сделал бы прежние строки непроверяемыми
молча, а это разлогинило бы весь дом.
"""

from __future__ import annotations

from backend.infrastructure.security.password_hasher import (
    ALGORITHM_PREFIX,
    DEFAULT_DIGEST,
    Pbkdf2PasswordHasher,
)


def test_hash_is_self_describing_and_verifies():
    """Сохранённая форма называет алгоритм и стоимость и проверяется на месте.

    Returns:
        None: Только проверка формата и сверки.
    """
    hasher = Pbkdf2PasswordHasher(iterations=1234, salt_bytes=16)

    stored = hasher.hash("correct horse")

    algorithm, recorded_iterations, salt, digest = stored.split("$")
    assert algorithm == f"{ALGORITHM_PREFIX}_{DEFAULT_DIGEST}"
    assert recorded_iterations == "1234"
    assert salt and digest
    assert hasher.verify("correct horse", stored) is True
    assert hasher.verify("wrong horse", stored) is False


def test_a_row_written_at_old_cost_still_verifies_after_cost_rises():
    """Строка, записанная с дешёвой стоимостью, проверяется и у дорогого хешера.

    Returns:
        None: Только проверка совместимости по вписанной в строку стоимости.
    """
    cheap = Pbkdf2PasswordHasher(iterations=100, salt_bytes=16)
    expensive = Pbkdf2PasswordHasher(iterations=600000, salt_bytes=16)

    stored = cheap.hash("reuse me")

    assert expensive.verify("reuse me", stored) is True


def test_foreign_algorithm_form_is_rejected_not_guessed():
    """Форму чужого алгоритма хешер отвергает, а не разбирает снисходительно.

    Returns:
        None: Только проверка отказа.
    """
    hasher = Pbkdf2PasswordHasher(iterations=100, salt_bytes=16)

    assert hasher.verify("x", "bcrypt$1$salt$digest") is False
