"""Хранилище настроек интерфейса одного аккаунта."""

from __future__ import annotations

from backend.application.interfaces.repositories.base import Loader, Saver
from backend.domain.entities.personalization.user_preferences import UserPreferences


class PreferencesRepository(Loader[UserPreferences], Saver[UserPreferences]):
    """Настройки интерфейса: одна строка на аккаунт."""
