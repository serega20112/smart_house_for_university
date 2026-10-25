"""Фраза о переключенном устройстве сверяется с перечислением состояний.

Раньше составитель ответа сравнивал значение с положением контакта `"ON"`, хотя
прикладной слой отдаёт состояние устройства: «включи лампа» отвечала «Лампа:
выключено», хотя лампа горела. Тест держит связь формулировки с настоящим
перечислением, потому что новый член перечисления не должен молча получить
неправильное слово.
"""

from __future__ import annotations

import pytest

from backend.application.dto.language.intent import Intent
from backend.application.use_cases.commands.result import CommandReply
from backend.domain.value_objects.devices.device_status import DeviceStatus
from backend.presentation.messages import CommandReplyComposer


def reply_of(status: DeviceStatus) -> CommandReply:
    """Возвращает ответ на команду переключения с этим состоянием устройства.

    Args:
        status: Состояние, которого устройство достигло.

    Returns:
        CommandReply: Ответ таким, каким его отдаёт прикладной слой.
    """
    return CommandReply(
        intent=Intent.SWITCH_DEVICE,
        answer="",
        details={"device": "Лампа", "status": status.value},
    )


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (DeviceStatus.OFF, "выключено"),
        (DeviceStatus.ACTIVE, "включено"),
        (DeviceStatus.COOLING, "включено"),
        (DeviceStatus.HEATING, "включено"),
        (DeviceStatus.HUMIDIFYING, "включено"),
        (DeviceStatus.DEHUMIDIFYING, "включено"),
        (DeviceStatus.UNAVAILABLE, "нет связи"),
    ],
)
def test_phrase_follows_the_domain_status(status: DeviceStatus, expected: str) -> None:
    """Каждое состояние получает своё слово, а не «выключено» по умолчанию."""
    assert CommandReplyComposer().for_result(reply_of(status)) == f"Лампа: {expected}."
