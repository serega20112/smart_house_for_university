"""Логин аккаунта.

Логин проверяет сам себя: аккаунт не может быть построен вокруг значения, которое
модель отвергает, поэтому никому в сценарии приложения не нужно помнить о вызове
валидатора перед сохранением.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.domain.exceptions import InvalidEmailError

PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_LENGTH = 254


@dataclass(frozen=True, slots=True, order=True)
class Email:
    """Приведённый к одному виду логин.

    Attributes:
        value: Адрес без окружающих пробелов, в нижнем регистре.

    Raises:
        InvalidEmailError: Когда значение пустое, слишком длинное или не похоже на
            адрес.
    """

    value: str

    def __post_init__(self) -> None:
        """Приводит логин к одному виду и проверяет его.

        Raises:
            InvalidEmailError: Когда значение пустое, слишком длинное или не похоже на
                адрес.
        """
        normalized = self.value.strip().lower()
        if not normalized:
            raise InvalidEmailError("is empty")
        if len(normalized) > MAX_LENGTH:
            raise InvalidEmailError(f"is longer than {MAX_LENGTH} characters")
        if not PATTERN.match(normalized):
            raise InvalidEmailError("does not look like an address")
        object.__setattr__(self, "value", normalized)

    @classmethod
    def parse(cls, raw: str) -> Email:
        """Строит логин из того, что набрал человек.

        Args:
            raw: Текст, введённый без какой-либо подготовки.

        Returns:
            Email: Приведённый логин.

        Raises:
            InvalidEmailError: Когда текст не годится как логин.
        """
        return cls(raw)
