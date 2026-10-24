"""Координация плат между процессами: реестр присутствия, шина команд, жизненный цикл платы.

Всё это нужно каждому процессу, а не только тому, что держит WebSocket. Реестр
присутствия и шина команд — общий язык между сервером плат и рабочим, а служба
жизненного цикла плат требуется рабочему для чистки просроченных объявлений. Сами
сокекты плат здесь не появляются: их заводит только процесс API.

Шлюз к железу связывается по-разному в зависимости от роли процесса — локально там, где
соединение рядом, и через шину там, где его нет, — поэтому здесь живут только общие
части, а привязка `BoardGateway` относится к провайдерам конкретной роли.
"""

from __future__ import annotations

from dishka import Provider, Scope, alias, provide
from redis.asyncio import Redis

from backend.application.interfaces.queries.board_queries import BoardQueries
from backend.application.interfaces.services.boards.board_availability import BoardAvailability
from backend.application.interfaces.services.boards.board_gateway import BoardGateway
from backend.application.interfaces.services.messaging.realtime_publisher import RealtimePublisher
from backend.application.interfaces.services.system.clock import Clock
from backend.application.interfaces.unit_of_work.board_onboarding import (
    BoardOnboardingUnitOfWorkFactory,
)
from backend.application.services.board_onboarding import BoardOnboardingService
from backend.config.settings import Settings
from backend.infrastructure.brokers.board_presence import RedisBoardPresence
from backend.infrastructure.brokers.command_bus import RedisBoardCommandBus

APP = Scope.APP


class BoardCoordinationProvider(Provider):
    """Разделённые между процессами реестр плат, шина команд и онбординг плат."""

    availability = alias(source=RedisBoardPresence, provides=BoardAvailability)

    @provide(scope=APP)
    def presence(self, redis: Redis, settings: Settings) -> RedisBoardPresence:
        """Собирает реестр подключённых плат поверх Redis.

        Args:
            redis: Асинхронное соединение Redis из провайдера брокеров.
            settings: Конфигурация, задающая префикс ключей и срок присутствия.

        Returns:
            RedisBoardPresence: Общий реестр присутствия плат.
        """
        return RedisBoardPresence(redis, settings.redis_key_prefix, settings.board_presence_ttl_sec)

    @provide(scope=APP)
    def command_bus(self, redis: Redis, settings: Settings) -> RedisBoardCommandBus:
        """Собирает шину команд платам поверх Redis Pub/Sub.

        Args:
            redis: Асинхронное соединение Redis из провайдера брокеров.
            settings: Конфигурация, задающая префикс каналов и срок ожидания ответа.

        Returns:
            RedisBoardCommandBus: Шина команд между процессами.
        """
        return RedisBoardCommandBus(
            redis, settings.redis_key_prefix, settings.board_command_result_timeout_sec
        )

    @provide(scope=APP)
    def board_onboarding(
        self,
        uow: BoardOnboardingUnitOfWorkFactory,
        queries: BoardQueries,
        boards: BoardGateway,
        realtime: RealtimePublisher,
        clock: Clock,
        settings: Settings,
    ) -> BoardOnboardingService:
        """Собирает жизненный цикл плат системы.

        Служба нужна и процессу интерфейса, и рабочему: первый выдаёт платам ключи и
        сопрягает их, второй снимает просроченные объявления. К железообращению
        `purge_expired_claims` не прикасается, поэтому рабочий обходится без собственного
        соединения с платами.
        """
        return BoardOnboardingService(
            onboarding_uow=uow,
            queries=queries,
            boards=boards,
            realtime=realtime,
            clock=clock,
            claim_ttl_sec=settings.board_claim_ttl_sec,
        )
