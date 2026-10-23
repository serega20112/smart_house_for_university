"""Интерфейс бота: разговор чата и обработчик входящих сообщений.

Транспорт бота живёт в инфраструктуре и не знает ни про какие команды. Здесь
решается, какой аккаунт стоит за чатом, что ответить на сообщение и как это
сообщение отдаётся библиотеке мессенджера. Фразы те же, что и у веб-интерфейса,
поэтому два канала не могут разойтись в формулировках.
"""

from backend.presentation.telegram.conversation import TelegramConversation
from backend.presentation.telegram.updates import TelegramUpdates

__all__ = [
    "TelegramConversation",
    "TelegramUpdates",
]
