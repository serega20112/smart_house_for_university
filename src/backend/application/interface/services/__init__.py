"""Порты сервисов: то, что приложение использует, но не реализует само.

Хэширование пароля, подпись токена, хранение изменчивого состояния, доступ к железу
и источник времени — не бизнес-правила, а внешние возможности. Их объявляют эти
интерфейсы, а реализуют — `infrastructure`, поэтому домен остаётся свободным от
криптографии и хранилищ.
"""

from backend.application.interface.services.board_gateway import BoardGateway
from backend.application.interface.services.board_report import BoardReport
from backend.application.interface.services.clock import Clock
from backend.application.interface.services.command_understanding_port import (
    CommandUnderstandingPort,
)
from backend.application.interface.services.distributed_lock import DistributedLock
from backend.application.interface.services.domain_event_dispatcher import (
    DomainEventDispatcher,
)
from backend.application.interface.services.home_device_directory import HomeDeviceDirectory
from backend.application.interface.services.home_state_store import HomeStateStore
from backend.application.interface.services.notification import Notification
from backend.application.interface.services.notification_factory import NotificationFactory
from backend.application.interface.services.password_hasher import PasswordHasher
from backend.application.interface.services.realtime_publisher import RealtimePublisher
from backend.application.interface.services.session_token_issuer import SessionTokenIssuer
from backend.application.interface.services.user_notifier import UserNotifier

__all__ = [
    "BoardGateway",
    "BoardReport",
    "Clock",
    "CommandUnderstandingPort",
    "DistributedLock",
    "DomainEventDispatcher",
    "HomeDeviceDirectory",
    "HomeStateStore",
    "Notification",
    "NotificationFactory",
    "PasswordHasher",
    "RealtimePublisher",
    "SessionTokenIssuer",
    "UserNotifier",
]
