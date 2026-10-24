"""Реестр провайдеров: `app` — подсистемы процесса, `use_cases` — сборка сценариев.

Здесь собрано всё, что знает контейнер. Порядок не важен: важны два правила, по которым
ищится нужный файл. Одиночный адаптер, живущий вместе с процессом, ищется в
`providers/app/<подсистема>.py`; сценарий — в `providers/use_cases/<фича>.py`, и класс
там называется `<Фича>UseCaseProvider`.
"""

from backend.infrastructure.di.providers.app.board_socket import BoardSocketProvider
from backend.infrastructure.di.providers.app.brokers import BrokersProvider
from backend.infrastructure.di.providers.app.database import DatabaseProvider
from backend.infrastructure.di.providers.app.persistence import PersistenceProvider
from backend.infrastructure.di.providers.app.phrases import PhrasesProvider
from backend.infrastructure.di.providers.app.runtime import RuntimeProvider
from backend.infrastructure.di.providers.app.security import SecurityProvider
from backend.infrastructure.di.providers.app.telegram import TelegramProvider
from backend.infrastructure.di.providers.app.websockets import WebSocketsProvider
from backend.infrastructure.di.providers.use_cases.accounts import AccountsUseCaseProvider
from backend.infrastructure.di.providers.use_cases.automation import AutomationUseCaseProvider
from backend.infrastructure.di.providers.use_cases.boards import BoardsUseCaseProvider
from backend.infrastructure.di.providers.use_cases.commands import CommandsUseCaseProvider
from backend.infrastructure.di.providers.use_cases.devices import DevicesUseCaseProvider
from backend.infrastructure.di.providers.use_cases.home import HomeUseCaseProvider
from backend.infrastructure.di.providers.use_cases.personalization import (
    PersonalizationUseCaseProvider,
)
from backend.infrastructure.di.providers.use_cases.scenarios import ScenariosUseCaseProvider

__all__ = [
    "AccountsUseCaseProvider",
    "AutomationUseCaseProvider",
    "BoardSocketProvider",
    "BoardsUseCaseProvider",
    "BrokersProvider",
    "CommandsUseCaseProvider",
    "DatabaseProvider",
    "DevicesUseCaseProvider",
    "HomeUseCaseProvider",
    "PersistenceProvider",
    "PersonalizationUseCaseProvider",
    "PhrasesProvider",
    "RuntimeProvider",
    "ScenariosUseCaseProvider",
    "SecurityProvider",
    "TelegramProvider",
    "WebSocketsProvider",
]
