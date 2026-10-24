"""Шлюз к железу для рабочего процесса: команды через шину, доступность из Redis.

Рабочий не держит WebSocket плат и не должен его заводить. Всё, что ему нужно для
управления железом, — это тот же самый интерфейс `BoardGateway`, но обращённый к шине
команд и общему реестру присутствия. Так прикладной слой рабочего не замечает разницы:
`DeviceControlService` работает с шлюзом одинаково в обоих процессах.

Этот провайдер включается только в контейнер рабочего; процесс API связывает
`BoardGateway` с локальным транспортом и в нём нужды нет.
"""

from __future__ import annotations

from dishka import Provider, Scope, provide

from backend.application.interfaces.services.boards.board_gateway import BoardGateway
from backend.infrastructure.brokers.board_presence import RedisBoardPresence
from backend.infrastructure.brokers.command_bus import RedisBoardCommandBus
from backend.infrastructure.esp.remote_gateway import RemoteBoardGateway

APP = Scope.APP


class BoardRemoteProvider(Provider):
    """Привязка шлюза к железу к шине команд — для процесса без соккетов плат."""

    @provide(scope=APP)
    def board_gateway(
        self, bus: RedisBoardCommandBus, presence: RedisBoardPresence
    ) -> BoardGateway:
        """Собирает удалённый шлюз: команды уходят в шину, доступность читается из реестра."""
        return RemoteBoardGateway(bus, presence)
