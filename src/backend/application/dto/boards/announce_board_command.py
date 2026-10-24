"""То, что плата сказала о себе, пока дозванивалась."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AnnounceBoardCommand:
    """Идентичность, которую плата предъявила при handshake.

    Attributes:
        device_key: Секрет, который плата предъявила.
        label: Короткий код, который плата сообщила, или пустая строка.
    """

    device_key: str
    label: str
