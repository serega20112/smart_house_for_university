"""Ответ главного экрана: весь дом одним снимком."""

from __future__ import annotations

from backend.application.dto.views.home_snapshot_view import HomeSnapshotView
from backend.presentation.api.responses.automation import AutomationResponse, automation_of
from backend.presentation.api.responses.common import StrictModel
from backend.presentation.api.responses.devices import DeviceResponse, device_of
from backend.presentation.api.responses.scenarios import ScenarioResponse, scenario_of


class ReadingResponse(StrictModel):
    """Значения климата такие, какими их видит интерфейс.

    Attributes:
        temperature: Измеренная температура или None.
        humidity: Измеренная относительная влажность или None.
    """

    temperature: float | None
    humidity: float | None


class HomeStateResponse(StrictModel):
    """Всё, что один экран интерфейса обязан нарисовать.

    Attributes:
        board_online: Подключена ли хоть одна плата аккаунта.
        automation_suspended: Держит ли ручное управление автоматизацию на паузе.
        reading: Значения климата сейчас.
        devices: Устройства с их текущим состоянием.
        automation: Настройка автоматизации.
        active_scenarios: Сценарии, которые ещё ставят себя выше автоматики.
    """

    board_online: bool
    automation_suspended: bool
    reading: ReadingResponse
    devices: list[DeviceResponse]
    automation: AutomationResponse
    active_scenarios: list[ScenarioResponse]


def snapshot_of(snapshot: HomeSnapshotView) -> HomeStateResponse:
    """Возвращает тело снимка дома.

    Args:
        snapshot: Снимок, собранный прикладным слоем одним выстрелом.

    Returns:
        HomeStateResponse: Тело главного экрана.
    """
    return HomeStateResponse(
        board_online=snapshot.board_online,
        automation_suspended=snapshot.automation_suspended,
        reading=ReadingResponse(
            temperature=snapshot.reading.temperature,
            humidity=snapshot.reading.humidity,
        ),
        devices=[device_of(device) for device in snapshot.devices],
        automation=automation_of(snapshot.automation),
        active_scenarios=[scenario_of(scenario) for scenario in snapshot.active_scenarios],
    )
