"""Реестр провайдеров: каждый — по одной части системы зависимостей."""

from backend.infrastructure.di.providers.accounts import AccountProvider
from backend.infrastructure.di.providers.automation import AutomationProvider
from backend.infrastructure.di.providers.boards import BoardProvider
from backend.infrastructure.di.providers.commands import CommandProvider
from backend.infrastructure.di.providers.core import CoreProvider
from backend.infrastructure.di.providers.devices import DeviceProvider
from backend.infrastructure.di.providers.domain import DomainProvider
from backend.infrastructure.di.providers.esp import EspProvider
from backend.infrastructure.di.providers.home import HomeProvider
from backend.infrastructure.di.providers.language import LanguageProvider
from backend.infrastructure.di.providers.persistence import PersistenceProvider
from backend.infrastructure.di.providers.scenarios import ScenarioProvider
from backend.infrastructure.di.providers.security import SecurityProvider
from backend.infrastructure.di.providers.telegram import TelegramProvider
from backend.infrastructure.di.providers.volatile import VolatileStateProvider

__all__ = [
    "AccountProvider",
    "AutomationProvider",
    "BoardProvider",
    "CommandProvider",
    "CoreProvider",
    "DeviceProvider",
    "DomainProvider",
    "EspProvider",
    "HomeProvider",
    "LanguageProvider",
    "PersistenceProvider",
    "ScenarioProvider",
    "SecurityProvider",
    "TelegramProvider",
    "VolatileStateProvider",
]
