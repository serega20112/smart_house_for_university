"""Графы обеих ролей собираются: у каждой свой шлюз и свои ресурсы процесса.

Здесь проверяется само разделение ролей: в процессе рабочего `BoardGateway` обязан
разрешаться в удалённый шлюз поверх шины команд, а не в локальный транспорт, который
поднимал бы второй сервер плат на занятом порту. Концентратор соединений интерфейса —
собственность процесса API, поэтому рабочему он не достаётся. Никакого железа, базы
или Redis не требуется — достаточно того, что граф строится и отдаёт правильные типы,
не касаясь сокета.
"""

from __future__ import annotations

import pytest

from backend.application.interfaces.services.boards.board_gateway import BoardGateway
from backend.application.services.device_control import DeviceControlService
from backend.config.settings import Settings
from backend.infrastructure.di import ProcessRole, build_dishka_container
from backend.infrastructure.di.dishka_container import ROLE_PROVIDERS
from backend.infrastructure.di.providers.app.board_socket import BoardSocketProvider
from backend.infrastructure.di.providers.app.websockets import WebSocketsProvider
from backend.infrastructure.esp.adapters import BoardGatewayAdapter
from backend.infrastructure.esp.remote_gateway import RemoteBoardGateway


def _providers_of(role: ProcessRole) -> tuple[object, ...]:
    """Возвращает ролевые провайдеры процесса.

    Args:
        role: Роль процесса.

    Returns:
        tuple[object, ...]: Провайдеры, добавленные к общим именно для этой роли.
    """
    return ROLE_PROVIDERS[role]


def test_worker_role_omits_board_socket_provider():
    """Рабочему не полагается провайдер транспорта плат.

    Returns:
        None: Только проверка состава ролевых провайдеров.
    """
    worker_providers = _providers_of(ProcessRole.WORKER)
    api_providers = _providers_of(ProcessRole.API)
    assert not any(isinstance(provider, BoardSocketProvider) for provider in worker_providers)
    assert any(isinstance(provider, BoardSocketProvider) for provider in api_providers)


def test_realtime_hub_provider_belongs_to_the_api_role():
    """Концентратор соединений интерфейса заводится только там, где есть интерфейс.

    Returns:
        None: Только проверка состава ролевых провайдеров.
    """
    worker_providers = _providers_of(ProcessRole.WORKER)
    api_providers = _providers_of(ProcessRole.API)
    assert not any(isinstance(provider, WebSocketsProvider) for provider in worker_providers)
    assert any(isinstance(provider, WebSocketsProvider) for provider in api_providers)


@pytest.mark.asyncio
async def test_worker_container_resolves_remote_gateway_without_socket():
    """Шлюз рабочего — удалённый, и его сборка не поднимает сервер плат.

    Returns:
        None: Только проверка типа разрешённого шлюза.
    """
    container = build_dishka_container(Settings(), role=ProcessRole.WORKER)
    try:
        gateway = await container.get(BoardGateway)
    finally:
        await container.close()

    assert isinstance(gateway, RemoteBoardGateway)
    assert not isinstance(gateway, BoardGatewayAdapter)


@pytest.mark.asyncio
async def test_worker_container_resolves_device_control_service():
    """Сервис управления железом собирается в рабочем, опираясь на удалённый шлюз.

    Returns:
        None: Только проверка разрешимости сервиса и его шлюза.
    """
    container = build_dishka_container(Settings(), role=ProcessRole.WORKER)
    try:
        service = await container.get(DeviceControlService)
        gateway = await container.get(BoardGateway)
    finally:
        await container.close()

    assert service is not None
    assert isinstance(gateway, RemoteBoardGateway)
