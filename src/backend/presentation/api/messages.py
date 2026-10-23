"""Wording of everything a person reads.

The application layer never writes user facing text: it asks for a message by name
and this module decides what that message says. The strings live in Russian
because the people using this system read Russian, and the interface is the only
place where the language of a person belongs.
"""

from __future__ import annotations

from backend.application.dto.language.intent import Intent
from backend.application.interface.services.notification import Notification
from backend.application.use_cases.commands.result import CommandReply

EMAIL_TAKEN = "Этот email уже занят."
INVALID_CREDENTIALS = "Неверный email или пароль."
INVALID_EMAIL = "Некорректный email."
INVALID_NAME = "Некорректное имя."
WEAK_PASSWORD = "Пароль слишком короткий."
CHANNEL_CONFLICT = "Этот канал реле уже занят другим устройством."
DEVICE_MISSING = "Устройство не найдено."
UNSUPPORTED_CAPABILITY = "Устройство не умеет выполнять эту команду."
BOARD_UNREACHABLE = "Плата не подтвердила команду."
SCENARIO_MISSING = "Сценарий не найден."
SCENARIO_ALREADY_FINISHED = "Сценарий уже завершён."
CLAIM_MISSING = "Предложение сопряжения не найдено."
CLAIM_EXPIRED = "Срок действия предложения сопряжения истёк."
CLAIM_TAKEN = "Плату уже сопрягли с другим аккаунтом."
COMMAND_NOT_UNDERSTOOD = "Не удалось понять команду."
LOGGED_OUT = "Вы вышли из аккаунта."
INVALID_DEVICE_NAME = "Некорректное имя устройства."
INVALID_RELAY_CHANNEL = "Некорректный канал реле."
INVALID_TEMPERATURE = "Некорректная температура."
INVALID_PAIRING_KEY = "Некорректный ключ сопряжения."
INVALID_NETWORK_PROFILE = "Некорректные параметры сети."
INVALID_DASHBOARD_LAYOUT = "Некорректная раскладка панели."
MALFORMED_IDENTIFIER = "Некорректный идентификатор."
COMMAND_NO_DATA = "Пока нет показаний датчиков."
COMMAND_CLIMATE = "Сейчас {temperature:.1f} °C и влажность {humidity:.0f} %."
COMMAND_DONE = "Готово."
TELEGRAM_LINK_INSTRUCTION = (
    "Аккаунт ещё не привязан к этому чату. Открой интерфейс, получи там код "
    "привязки и пришли его сообщением вида link:<код>."
)
TELEGRAM_EMPTY_COMMAND = "Пришли команду текстом, например: «выключи свет»."
TELEGRAM_LINKED = "Чат привязан к аккаунту. Команду можно писать прямо сюда."
INTERNAL_FAILURE = "Внутренняя ошибка сервера."


def error_detail(message: str) -> dict[str, str]:
    """Return the body of a failed request.

    Args:
        message: Text shown to the person.

    Returns:
        dict[str, str]: Body with the message under the key FastAPI expects.
    """
    return {"detail": message}


class SimpleNotification(Notification):
    """A message with a text and a severity behind it.

    Attributes:
        _text: Text shown to the person.
        _severity: How urgent the message is.

    """

    def __init__(self, text: str, severity: str = "info") -> None:
        """Initialize the notification.

        Args:
            text: Text shown to the person.
            severity: How urgent the message is.

        Returns:
            None.
        """
        self._text = text
        self._severity = severity

    @property
    def text(self) -> str:
        """Return the message as it reaches the person.

        Returns:
            str: Rendered message.
        """
        return self._text

    @property
    def severity(self) -> str:
        """Return how urgent the message is.

        Returns:
            str: One of the severities the channels understand.
        """
        return self._severity


class NotificationFactoryImpl:
    """Builds the wording of every message a person may receive.

    The application asks for a message by name, so the wording of the system is
    decided in one place instead of being written into the use cases.
    """

    def board_online(self) -> Notification:
        """Return the message shown when a board comes back.

        Returns:
            Notification: Message to deliver.
        """
        return SimpleNotification("Плата снова на связи.")

    def board_offline(self) -> Notification:
        """Return the message shown when a board goes away.

        Returns:
            Notification: Message to deliver.
        """
        return SimpleNotification("Плата потеряла связь.", "warning")

    def scenario_started(self, scenario_id: str, target: str | None) -> Notification:
        """Return the message shown when a scenario begins acting.

        Args:
            scenario_id: Identifier of the scenario.
            target: Area or object the user named.

        Returns:
            Notification: Message to deliver.
        """
        del scenario_id
        subject = f" для «{target}»" if target else ""
        return SimpleNotification(f"Сценарий{subject} начал работу.")

    def scenario_progress(self, scenario_id: str, temperature: float | None) -> Notification:
        """Return the periodic progress message of a running scenario.

        Args:
            scenario_id: Identifier of the scenario.
            temperature: Current temperature or None.

        Returns:
            Notification: Message to deliver.
        """
        del scenario_id
        if temperature is None:
            return SimpleNotification("Сценарий выполняется, температура неизвестна.")
        return SimpleNotification(f"Сценарий выполняется, сейчас {temperature:.1f} °C.")

    def scenario_finished(self, scenario_id: str, reason: str) -> Notification:
        """Return the message shown when a scenario reaches a final stage.

        Args:
            scenario_id: Identifier of the scenario.
            reason: Why it reached that stage.

        Returns:
            Notification: Message to deliver.
        """
        del scenario_id, reason
        return SimpleNotification("Сценарий завершён.")

    def scenario_failed(self, scenario_id: str, reason: str) -> Notification:
        """Return the message shown when a scenario could not be carried out.

        Args:
            scenario_id: Identifier of the scenario.
            reason: Why it failed.

        Returns:
            Notification: Message to deliver.
        """
        del scenario_id, reason
        return SimpleNotification("Сценарий не удалось выполнить.", "warning")


class CommandReplyComposer:
    """Turns the structured result of a command into a phrase.

    The application reports *what* happened, and this class decides *how* to say
    it. Keeping the two apart is what lets the same result be printed in the chat
    and rendered in the browser without two drifting copies of the wording.
    """

    def for_result(self, result: object) -> str:
        """Return the phrase describing what a command produced.

        Args:
            result: Structured result of a dispatched command.

        Returns:
            str: Phrase for the user.
        """
        if not isinstance(result, CommandReply):
            return str(result)
        details = result.details
        match result.intent:
            case Intent.SWITCH_DEVICE:
                device = details.get("device")
                return f"{device}: {self._status(details.get('status'))}."
            case Intent.SWITCH_ALL:
                devices = details.get("devices")
                if not devices:
                    return "Нечего переключать: подходящих устройств нет."
                return "Переключил: " + ", ".join(str(name) for name in devices) + "."
            case Intent.SET_TEMPERATURE:
                return f"Целевая температура теперь {self._number(details.get('temperature'))} °C."
            case Intent.SET_HUMIDITY:
                return f"Целевая влажность теперь {self._number(details.get('humidity'))} %."
            case Intent.RUN_CAPABILITY:
                device = details.get("device")
                return f"{device}: команда выполнена."
            case Intent.DESCRIBE_HOME:
                return self._describe(details)
            case Intent.READ_TEMPERATURE:
                value = details.get("temperature")
                return COMMAND_NO_DATA if value is None else f"Сейчас {self._number(value)} °C."
            case Intent.READ_HUMIDITY:
                value = details.get("humidity")
                return COMMAND_NO_DATA if value is None else f"Влажность {self._number(value)} %."
            case Intent.SCHEDULE_SCENARIO:
                start_at = details.get("start_at")
                return f"Сценарий запущен, начало в {start_at}." if start_at else COMMAND_DONE
            case Intent.CANCEL_SCENARIO:
                return "Сценарий отменён."
        return COMMAND_DONE

    def _describe(self, details: dict[str, object]) -> str:
        temperature = details.get("temperature")
        humidity = details.get("humidity")
        if temperature is None and humidity is None:
            return COMMAND_NO_DATA
        if humidity is None:
            return f"Сейчас {self._number(temperature)} °C."
        if temperature is None:
            return f"Влажность {self._number(humidity)} %."
        return COMMAND_CLIMATE.format(
            temperature=float(str(temperature)), humidity=float(str(humidity))
        )

    @staticmethod
    def _status(raw: object) -> str:
        return "включено" if raw == "ON" else "выключено"

    @staticmethod
    def _number(raw: object) -> str:
        try:
            return f"{float(str(raw)):.1f}".removesuffix(".0")
        except (TypeError, ValueError):
            return "неизвестно"
