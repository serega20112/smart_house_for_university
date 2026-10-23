"""Разбор сырых значений переменных окружения."""

from __future__ import annotations

TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def as_bool(raw: str) -> bool:
    """Превращает строку окружения в признак.

    Args:
        raw: Значение переменной окружения.

    Returns:
        bool: True для "1", "true", "yes" и "on" независимо от регистра.
    """
    return raw.strip().lower() in TRUE_VALUES


def as_list(raw: str) -> list[str]:
    """Режет строку окружения по запятым, убирая пробелы и пустые части."""
    return [item.strip() for item in raw.split(",") if item.strip()]
