"""Пароль в открытом виде — до того, как его сохранят хешированием.

Правило длины живёт здесь, рядом со значением, а не в методе агрегата: в агрегат и к
хешеру не должен уходить пароль, который домен отверг бы. Сам агрегат хранит только
результат хеширования и о сыром пароле не знает.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.exceptions import WeakPasswordError

MIN_PASSWORD_LENGTH = 8


@dataclass(frozen=True, slots=True)
class RawPassword:
    """Набранный человеком пароль, проверенный по длине.

    Attributes:
        value: Пароль таким, каким его ввели.

    Raises:
        WeakPasswordError: Когда пароль короче разрешённого.
    """

    value: str

    def __post_init__(self) -> None:
        """Проверяет длину набранного пароля.

        Raises:
            WeakPasswordError: Когда пароль короче разрешённого.
        """
        if len(self.value) < MIN_PASSWORD_LENGTH:
            raise WeakPasswordError(MIN_PASSWORD_LENGTH)
