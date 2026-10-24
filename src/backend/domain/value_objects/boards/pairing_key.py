"""Секрет, который плата предъявляет при дозвоне.

Ключ — учётные данные платы, поэтому это объект-значение, один раз отвергающий
неподходящее значение вместо опечатки, из-за которой плата не смогла бы соединиться
никогда.
"""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass
from typing import Self

from backend.domain.exceptions import InvalidPairingKeyError

PATTERN = re.compile(r"^[A-Za-z0-9]{8,64}$")


@dataclass(frozen=True, slots=True, order=True)
class PairingKey:
    """Секрет, связывающий плату с аккаунтом.

    Attributes:
        value: Ключ таким, каким его предъявили при handshake.

    Raises:
        InvalidPairingKeyError: Когда ключ пустой или неподходящей формы.
    """

    value: str

    def __post_init__(self) -> None:
        """Проверяет форму ключа.

        Raises:
            InvalidPairingKeyError: Когда ключ пустой или неподходящей формы.
        """
        trimmed = self.value.strip()
        if not trimmed:
            raise InvalidPairingKeyError("is empty")
        if not PATTERN.match(trimmed):
            raise InvalidPairingKeyError("contains characters a key cannot have")
        object.__setattr__(self, "value", trimmed)

    def __str__(self) -> str:
        """Возвращает замаскированную форму, которую пишут в журнал.

        Returns:
            str: Первые символы и постоянная маска вместо остального.
        """
        return f"{self.value[:4]}..."

    @classmethod
    def generate(cls) -> Self:
        """Вырабатывает ключ плате, сопряжённой из интерфейса.

        Returns:
            Self: Свежий ключ.
        """
        return cls(secrets.token_hex(16))

    @classmethod
    def derive_from_chip(cls, chip_id: int) -> Self:
        """Вырабатывает ключ, который новая плата хранит у себя в памяти.

        Идентификатор чипа делает каждую плату разной без доверия к какому-либо
        источнику случайности на старте, а случайный хвост разъединяет две платы,
        прошитые одним и тем же бинарником.

        Args:
            chip_id: Идентификатор чипа, уникальный для каждой платы.

        Returns:
            Self: Ключ, который плата будет предъявлять дальше.
        """
        return cls(f"{chip_id:06x}{secrets.token_hex(13)}")
