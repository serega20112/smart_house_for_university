"""Концентратор, раздающий события интерфейсу в реальном времени.

Прикладной слой публикует события через Redis, поэтому их доставляет и тот
процесс, где нет ни одного сокета: каждый экземпляр бэкенда обменивается
сообщениями через брокер, а тот, у которого держится соединение аккаунта,
отдаёт их браузеру.

Клиенты сгруппированы по аккаунту, под которым они вошли, и событие уходит
только в сокеты собственного владельца, поэтому один человек не увидит чужой дом.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections import defaultdict

from fastapi import WebSocket

from backend.domain.identifiers import UserId
from backend.infrastructure.brokers.event_broker import RedisSubscriber
from backend.infrastructure.system.logging import get_logger

log = get_logger("websocket.hub")


class WebSocketHub:
    """Отдаёт события каждого аккаунта в сокеты этого аккаунта.

    Args:
        subscriber: Читатель каналов событий Redis.
    """

    def __init__(self, subscriber: RedisSubscriber) -> None:
        """Инициализирует пустой концентратор.

        Args:
            subscriber: Читатель каналов событий Redis.
        """
        self._subscriber = subscriber
        self._clients: dict[UserId, set[WebSocket]] = defaultdict(set)
        self._readers: dict[UserId, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: UserId, websocket: WebSocket) -> None:
        """Принимает новое соединение и следит, чтобы события в него доходили.

        Args:
            user_id: Аккаунт, под которым соединение разрешено.
            websocket: Соединение клиента.
        """
        await websocket.accept()
        async with self._lock:
            self._clients[user_id].add(websocket)
            if user_id not in self._readers:
                self._readers[user_id] = asyncio.create_task(
                    self._pump(user_id), name=f"events-{user_id}"
                )
        log.info("websocket.client_connected", user=str(user_id), clients=self._count())

    async def disconnect(self, user_id: UserId, websocket: WebSocket) -> None:
        """Забирает соединение и перестаёт читать для опустевшего аккаунта.

        Args:
            user_id: Аккаунт, под которым соединение разрешено.
            websocket: Соединение клиента.
        """
        async with self._lock:
            self._clients[user_id].discard(websocket)
            if self._clients[user_id]:
                return
            self._clients.pop(user_id, None)
            reader = self._readers.pop(user_id, None)
        if reader is not None:
            reader.cancel()

    async def stop(self) -> None:
        """Останавливает всех читателей этого процесса."""
        async with self._lock:
            readers = list(self._readers.values())
            self._readers.clear()
            self._clients.clear()
        for reader in readers:
            reader.cancel()
        for reader in readers:
            with contextlib.suppress(asyncio.CancelledError):
                await reader

    async def _pump(self, user_id: UserId) -> None:
        """Пересылает каждое событие аккаунта в его сокеты.

        Сокет, которому не удалось принять сообщение, отбрасывается; отказ всей
        подписки записывается в журнал и повторяется после паузы: сбой Redis не
        должен надолго глушить интерфейс.

        Args:
            user_id: Аккаунт, чей канал читается.
        """
        while True:
            try:
                async for event in self._subscriber.stream(user_id):
                    await self._deliver(user_id, event.event, event.payload)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                log.warning("websocket.reader_failed", user=str(user_id), error=str(error))
                await asyncio.sleep(1.0)

    async def _deliver(self, user_id: UserId, event: str, payload: dict) -> None:
        """Отправляет одно событие всем сокетам аккаунта, отцепив отказавшие."""
        async with self._lock:
            clients = list(self._clients.get(user_id, ()))
        if not clients:
            return
        message = {"type": event, "payload": payload}
        for client in clients:
            try:
                await client.send_json(message)
            except Exception:
                await self.disconnect(user_id, client)

    def _count(self) -> int:
        """Возвращает число клиентских соединений, которые концентратор держит."""
        return sum(len(clients) for clients in self._clients.values())
