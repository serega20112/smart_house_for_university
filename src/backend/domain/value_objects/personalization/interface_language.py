"""
Язык, на котором говорит интерфейс.

Значение само по себе, поэтому не делит файл с настройками проекции.
"""

from __future__ import annotations

from enum import StrEnum


class InterfaceLanguage(StrEnum):
    """Язык, на котором говорит интерфейс."""

    RUSSIAN = "ru"
    ENGLISH = "en"
