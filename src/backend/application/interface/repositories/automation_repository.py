"""Хранилище настроек автоматизации одного аккаунта.

Чтение возвращает None для аккаунта, который никогда не настраивал автоматизацию,
вместо того чтобы молча вставить строку со значениями по умолчанию: именно поэтому
select не превращается в write за спиной вызывающего.
"""

from __future__ import annotations

from backend.application.interface.repositories.base import Loader, Saver
from backend.domain.aggregates.automation.automation_settings import AutomationSettings


class AutomationRepository(Loader[AutomationSettings], Saver[AutomationSettings]):
    """Настройки автоматизации: одна строка на аккаунт."""
