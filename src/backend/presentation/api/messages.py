"""Human readable messages for operation results.

Presentation owns the wording of every answer, so business code stays free of
user facing text and can be reused by any channel.
"""

from __future__ import annotations

from typing import Any

from backend.application.dto.command import CommandResult
from backend.application.dto.device import DeviceExecutionResult
from backend.application.use_cases.device import TurnAllResult
from backend.domain.enums.device import Capability
from backend.domain.enums.operation import ClarificationReason, OperationStatus

CLARIFY_MESSAGES: dict[ClarificationReason, str] = {
    ClarificationReason.UNRECOGNIZED_INTENT: (
        "Не уверен, что правильно понял. Уточните, пожалуйста, команду."
    ),
    ClarificationReason.LOW_CONFIDENCE: (
        "Не уверен, что правильно понял. Уточните, пожалуйста, команду."
    ),
    ClarificationReason.UNKNOWN_DEVICE: "Не нашёл такое устройство. Какое именно имеете в виду?",
    ClarificationReason.MISSING_TEMPERATURE: "Какую температуру поставить?",
    ClarificationReason.MISSING_HUMIDITY: "Какую влажность поставить?",
    ClarificationReason.MISSING_CAPABILITY: (
        "Не нашёл устройство, которое умеет это делать."
    ),
}

CAPABILITY_ACTIONS: dict[Capability, str] = {
    Capability.ON: "Включаю",
    Capability.OFF: "Выключаю",
    Capability.COOL: "Включаю охлаждение",
    Capability.HEAT: "Включаю нагрев",
}

STATUS_DETAILS: dict[OperationStatus, str] = {
    OperationStatus.SUCCESS: "Готово.",
    OperationStatus.NOT_FOUND: "Объект не найден.",
    OperationStatus.UNAVAILABLE: "ESP8266 недоступна, команда не выполнена.",
    OperationStatus.UNSUPPORTED: "Нет устройства, способного это выполнить.",
    OperationStatus.CHANNEL_CONFLICT: "Канал уже занят другим устройством.",
    OperationStatus.INVALID_INPUT: "Некорректное значение.",
    OperationStatus.FAILED: "Не удалось выполнить команду.",
}


def execution_message(result: DeviceExecutionResult) -> str:
    """Return the reply text of a device command.

    Args:
        result: Result of the command.

    Returns:
        str: Reply text.
    """
    if not result.ok:
        return STATUS_DETAILS[result.status]
    device = result.device
    action = CAPABILITY_ACTIONS.get(result.capability, "Переключаю")
    return f"{action}: {device.name}." if device is not None else f"{action}."


def turn_all_message(result: TurnAllResult, on: bool) -> str:
    """Return the reply text of a switch all command.

    Args:
        result: Result of the command.
        on: Whether the devices were switched on.

    Returns:
        str: Reply text.
    """
    names = [result.device.name for result in result.switched if result.device is not None]
    if not names:
        return "Нет доступных устройств."
    verb = "Включено" if on else "Выключено"
    return f"{verb}: {', '.join(names)}."


def command_message(result: CommandResult) -> str:
    """Return the reply text of a free-form command.

    Args:
        result: Structured answer of the command use case.

    Returns:
        str: Reply text.
    """
    if result.clarification is not None:
        return CLARIFY_MESSAGES[result.clarification]
    if not result.ok:
        return STATUS_DETAILS[result.status]
    details = result.details or {}
    if "temperature" in details and result.intent == "SET_TEMPERATURE":
        return f"Целевая температура: {details['temperature']}°C."
    if "humidity" in details and result.intent == "SET_HUMIDITY":
        return f"Целевая влажность: {details['humidity']}%"
    if result.scenario_id is not None:
        return f"Сценарий #{result.scenario_id} создан."
    if result.intent in ("TURN_ON_ALL", "TURN_OFF_ALL"):
        names = [device.name for device in details.get("devices", [])]
        return f"Готово: {', '.join(names)}." if names else STATUS_DETAILS[result.status]
    if result.intent in ("TURN_ON", "TURN_OFF", "COOL", "HEAT"):
        device = details.get("device")
        capability = _capability_for(result.intent)
        action = CAPABILITY_ACTIONS.get(capability, "Готово")
        return f"{action}: {device.name}." if device is not None else f"{action}."
    return describe_read_intent(result.intent, details)


def describe_read_intent(intent: str | None, details: dict[str, Any]) -> str:
    """Return the reply text of an intent that only reads the state.

    Args:
        intent: Recognized intent.
        details: Structured details of the answer.

    Returns:
        str: Reply text.
    """
    if intent == "GET_TEMPERATURE":
        value = details.get("temperature")
        return "Данных нет." if value is None else f"Температура: {value:.1f}°C."
    if intent == "GET_HUMIDITY":
        value = details.get("humidity")
        return "Данных нет." if value is None else f"Влажность: {value:.0f}%."
    if intent == "GET_STATUS":
        return describe_state(details)
    if intent == "CANCEL_SCENARIO":
        return "Активных сценариев нет."
    return STATUS_DETAILS[OperationStatus.SUCCESS]


def describe_state(details: dict[str, Any]) -> str:
    """Return a textual summary of the home state.

    Args:
        details: Structured details of the answer.

    Returns:
        str: Reply text.
    """
    esp = "на связи" if details.get("esp_online") else "недоступна"
    override = "вкл" if details.get("manual_override") else "выкл"
    scenarios = details.get("active_scenarios") or []
    return (
        f"ESP8266: {esp}. Автоматизация: {override}. "
        f"Активных сценариев: {len(scenarios)}."
    )


def not_found_message(subject: str, identifier: object) -> str:
    """Return the reply text of a missing object.

    Args:
        subject: Kind of the object.
        identifier: Identifier that was requested.

    Returns:
        str: Reply text.
    """
    return f"{subject} {identifier} не найден."


def device_missing_message(device_id: object) -> str:
    """Return the reply text of a missing device.

    Args:
        device_id: Identifier that was requested.

    Returns:
        str: Reply text.
    """
    return not_found_message("Устройство", device_id)


def unknown_mode_message() -> str:
    """Return the reply text of an unknown device mode.

    Returns:
        str: Reply text.
    """
    return "Неизвестный режим."


def created_message(subject: str, name: str) -> str:
    """Return the reply text of a created object.

    Args:
        subject: Kind of the object.
        name: Name of the object.

    Returns:
        str: Reply text.
    """
    return f"{subject} «{name}» создан."


def updated_message(subject: str, name: str) -> str:
    """Return the reply text of an updated object.

    Args:
        subject: Kind of the object.
        name: Name of the object.

    Returns:
        str: Reply text.
    """
    return f"{subject} «{name}» обновлён."


def deleted_message(subject: str, identifier: object) -> str:
    """Return the reply text of a deleted object.

    Args:
        subject: Kind of the object.
        identifier: Identifier of the object.

    Returns:
        str: Reply text.
    """
    return f"{subject} {identifier} удалён."


def settings_saved_message() -> str:
    """Return the reply text of saved automation settings.

    Returns:
        str: Reply text.
    """
    return "Настройки автоматизации обновлены."


def automation_toggled_message(enabled: bool) -> str:
    """Return the reply text of a toggled automation mode.

    Args:
        enabled: Desired state of the automation mode.

    Returns:
        str: Reply text.
    """
    return f"Автоматизация {'включена' if enabled else 'выключена'}."


def scenario_cancelled_message(scenario_id: int) -> str:
    """Return the reply text of a cancelled scenario.

    Args:
        scenario_id: Identifier of the scenario.

    Returns:
        str: Reply text.
    """
    return f"Сценарий #{scenario_id} отменён."


def channel_conflict_message(channel: int) -> str:
    """Return the reply text of a conflicting channel assignment.

    Args:
        channel: Physical relay channel.

    Returns:
        str: Reply text.
    """
    return f"Канал {channel} уже занят."


def invalid_temperature_message() -> str:
    """Return the reply text of an out of range temperature.

    Returns:
        str: Reply text.
    """
    return "Температура вне диапазона −10..45°C."


def invalid_humidity_message() -> str:
    """Return the reply text of an out of range humidity.

    Returns:
        str: Reply text.
    """
    return "Влажность вне диапазона 0..100%."


def _capability_for(intent: str | None) -> Capability | None:
    return {
        "TURN_ON": Capability.ON,
        "TURN_OFF": Capability.OFF,
        "COOL": Capability.COOL,
        "HEAT": Capability.HEAT,
    }.get(intent or "")


def preferences_saved_message() -> str:
    """Return the reply text of saved interface preferences.

    Returns:
        str: Reply text.
    """
    return "Настройки интерфейса обновлены."


def dashboard_saved_message() -> str:
    """Return the reply text of a saved dashboard layout.

    Returns:
        str: Reply text.
    """
    return "Состав главного экрана обновлён."


def board_paired_message() -> str:
    """Return the reply text of a newly paired board.

    Returns:
        str: Reply text.
    """
    return "Плата сопряжена. Впишите ключ сопряжения в прошивку."


def board_unpaired_message(device_id: int) -> str:
    """Return the reply text of an unpaired board.

    Args:
        device_id: Identifier of the board.

    Returns:
        str: Reply text.
    """
    return f"Плата #{device_id} отвязана."


def board_claimed_message(name: str) -> str:
    """Return the reply text of a board an account just took.

    Args:
        name: Name the user gave to the board.

    Returns:
        str: Reply text.
    """
    return f"Плата «{name}» привязана к вашему аккаунту."


def claim_taken_message() -> str:
    """Return the reply text of a board another account already took.

    Returns:
        str: Reply text.
    """
    return "Эту плату уже забрал другой пользователь."


def claim_expired_message() -> str:
    """Return the reply text of an offer nobody took in time.

    Returns:
        str: Reply text.
    """
    return "Плата перестала искать владельца. Включите её заново и повторите."


def voice_no_speech_message() -> str:
    """Return the reply text of an empty phrase.

    Returns:
        str: Reply text.
    """
    return "Я ничего не услышал."


def voice_unavailable_message() -> str:
    """Return the reply text of a voice service that cannot answer.

    Returns:
        str: Reply text.
    """
    return "Голосовой модуль сейчас недоступен."


def voice_armed_message() -> str:
    """Return the reply text of an opened recording window.

    Returns:
        str: Reply text.
    """
    return "Микрофон включён, слушаю."


def voice_disarmed_message() -> str:
    """Return the reply text of a closed recording window.

    Returns:
        str: Reply text.
    """
    return "Микрофон выключен."


def voice_board_offline_message() -> str:
    """Return the reply text of a microphone request for an absent board.

    Returns:
        str: Reply text.
    """
    return "Плата ESP8266 сейчас не на связи, включить микрофон не могу."


def voice_disabled_message() -> str:
    """Return the reply text of a voice pipeline that is switched off.

    Returns:
        str: Reply text.
    """
    return "Голосовое управление выключено на сервере."


def voice_status_message(
    active: bool, continuous: bool, sample_rate: int, max_audio_sec: int, online: bool
) -> str:
    """Return the reply text describing the state of the voice pipeline.

    Args:
        active: Whether a voice service is configured.
        continuous: Whether listening resumes automatically.
        sample_rate: Samples per second requested from the board.
        max_audio_sec: Longest phrase accepted from the board.
        online: Whether a board of the user is connected.

    Returns:
        str: Reply text.
    """
    if not active:
        return voice_disabled_message()
    listening = "непрерывно" if continuous else "по запросу"
    board = "на связи" if online else "не на связи"
    return (
        f"Голос включён, сервис распознавания {board}, "
        f"режим {listening}, {sample_rate} Гц, до {max_audio_sec} с."
    )