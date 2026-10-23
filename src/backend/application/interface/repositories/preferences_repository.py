"""Хранилище настроек интерфейса одного аккаунта."""

from __future__ import annotations

from backend.application.interface.repositories.base import Loader, Saver
from backend.domain.aggregates.preferences.user_preferences import UserPreferences


class PreferencesRepository(Loader[UserPreferences], Saver[UserPreferences]):
    """Настройки интерфейса: одна строка на аккаунт."""
