"""
Визуальная тема интерфейса.

Перечисление живёт своим файлом: оно описывает значение, а не настройки аккаунта,
у которых есть своя жизнь и свои инварианты.
"""

from __future__ import annotations

from enum import StrEnum


class Theme(StrEnum):
    """Визуальная тема интерфейса."""

    DARK = "dark"
    LIGHT = "light"
