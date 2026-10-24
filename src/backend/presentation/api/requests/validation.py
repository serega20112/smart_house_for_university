"""Сверка значений запроса со словарём домена.

Pydantic превращает в отказ ввода только ValueError, а домен бросает собственные
исключения. Мост между ними живёт здесь: значение, которое домен не узнаёт,
становится отказом валидации с тем же текстом, а не аварийным ответом сервера.
"""

from __future__ import annotations

from collections.abc import Callable

from backend.domain.exceptions import DomainError


def known_to_domain[Parsed](parser: Callable[[str], Parsed], value: str) -> str:
    """Проверяет, что домен узнаёт значение, и возвращает его без изменений.

    Args:
        parser: Разбор домена для этого вида значений.
        value: Значение из тела запроса.

    Returns:
        str: То же значение, если домен его узнаёт.

    Raises:
        ValueError: Когда домен значение отверг.
    """
    try:
        parser(value)
    except DomainError as error:
        raise ValueError(str(error)) from error
    return value
