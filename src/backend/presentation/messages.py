"""Формулировки всего, что человек читает.

Прикладной слой никогда не пишет текст для человека: он просит сообщение по имени,
а решает, что в этом сообщении будет сказано, этот модуль. Фразы русские, потому
что русские — люди, которые системой пользуются, и интерфейс — единственное место,
где язык человека вообще появляется.
"""

from __future__ import annotations

from backend.application.dto.language.intent import Intent
from backend.application.interfaces.services.messaging.notification import Notification
from backend.application.use_cases.commands.result import CommandReply

EMAIL_TAKEN = "Этот email уже занят."
INVALID_CREDENTIALS = "Неверный email или пароль."
INVALID_EMAIL = "Некорректный email."
INVALID_NAME = "Некорректное имя."
WEAK_PASSWORD = "Пароль слишком короткий."
CHANNEL_CONFLICT = "Этот канал реле уже занят другим устройством."
DEVICE_MISSING = "Устройство не найдено."
BOARD_MISSING = "Плата не найдена."
BOARD_HAS_DEVICES = (
    "Плата ещё управляет устройствами: {devices}. "
    "Оставьте их в доме без платы или удалите вместе с настройкой."
)
UNSUPPORTED_CAPABILITY = "Устройство не умеет выполнять эту команду."
CAPABILITY_UNSUPPORTED = "Ни одно устройство дома не умеет выполнять эту команду."
BOARD_UNREACHABLE = "Плата не подтвердила команду."
BOARD_NOT_CHOSEN = "Плат в доме несколько: выберите, к какой привязано устройство."
SCENARIO_MISSING = "Сценарий не найден."
SCENARIO_ALREADY_FINISHED = "Сценарий уже завершён."
ILLEGAL_SCENARIO_TRANSITION = "Сценарий нельзя перевести в это состояние."
STATE_CHANGED = "Состояние изменилось, обновите страницу и повторите."
SESSION_OWNER_MISSING = "Аккаунт этой сессии больше не существует."
CLAIM_MISSING = "Предложение сопряжения не найдено."
CLAIM_EXPIRED = "Срок действия предложения сопряжения истёк."
CLAIM_TAKEN = "Плату уже сопрягли с другим аккаунтом."
COMMAND_NOT_UNDERSTOOD = "Не удалось понять команду."
LANGUAGE_MODEL_UNAVAILABLE = (
    "Смысловой разбор фраз сейчас недоступен. Переформулируйте просьбу привычными словами."
)
LOGGED_OUT = "Вы вышли из аккаунта."
UNAUTHORIZED = "Требуется авторизация."
INVALID_DEVICE_NAME = "Некорректное имя устройства."
INVALID_DEVICE_KIND = "Некорректный тип устройства."
INVALID_CAPABILITY = "Некорректная способность устройства."
INVALID_BOARD_NAME = "Некорректное имя платы."
INVALID_RELAY_CHANNEL = "Некорректный канал реле."
INVALID_TEMPERATURE = "Некорректная температура."
INVALID_HUMIDITY = "Некорректная влажность."
INVALID_TOLERANCE = "Некорректный допуск температуры."
INVALID_COMPLETION_BEHAVIOR = "Некорректное поведение завершения сценария."
INVALID_SCENARIO_TARGET = "Слишком длинное название места или предмета сценария."
INVALID_WIDGET_KIND = "Некорректный вид виджета."
INVALID_PAIRING_KEY = "Некорректный ключ сопряжения."
INVALID_NETWORK_PROFILE = "Некорректные параметры сети."
INVALID_DASHBOARD_LAYOUT = "Некорректная раскладка панели."
DASHBOARD_ACCESS_DENIED = "Виджет ссылается на чужое устройство."
MALFORMED_IDENTIFIER = "Некорректный идентификатор."
COMMAND_NO_DATA = "Пока нет показаний датчиков."
COMMAND_CLIMATE = "Сейчас {temperature:.1f} °C и влажность {humidity:.0f} %."
COMMAND_DONE = "Готово."
COMMAND_NOTHING_TO_SWITCH = "Нечего переключать: подходящих устройств нет."
COMMAND_SWITCHED = "Переключил: "
COMMAND_SWITCHED_PARTIAL = "Переключил: {devices}. Не ответили: {failed}."
COMMAND_TARGET_TEMPERATURE = "Целевая температура теперь {value} °C."
COMMAND_TARGET_HUMIDITY = "Целевая влажность теперь {value} %."
COMMAND_CAPABILITY_DONE = "{device}: команда выполнена."
COMMAND_DEVICE_STATE = "{device}: {state}."
COMMAND_NOW_TEMPERATURE = "Сейчас {value} °C."
COMMAND_NOW_HUMIDITY = "Влажность {value} %."
COMMAND_SCENARIO_STARTED = "Сценарий запущен, начало в {start_at}."
COMMAND_SCENARIO_CANCELLED = "Сценарий отменён."
STATUS_ON = "включено"
STATUS_OFF = "выключено"
UNKNOWN_VALUE = "неизвестно"
TELEGRAM_LINK_INSTRUCTION = (
    "Аккаунт ещё не привязан к этому чату. Открой интерфейс, получи там код "
    "привязки и пришли его сообщением вида link:<код>."
)
TELEGRAM_EMPTY_COMMAND = "Пришли команду текстом, например: «выключи свет»."
TELEGRAM_LINKED = "Чат привязан к аккаунту. Команду можно писать прямо сюда."
INTERNAL_FAILURE = "Внутренняя ошибка сервера."


def error_detail(message: str) -> dict[str, str]:
    """Возвращает тело отказного запроса.

    Args:
        message: Текст, который увидит человек.

    Returns:
        dict[str, str]: Тело с фразой под тем ключом, которого ждёт FastAPI.
    """
    return {"detail": message}


class SimpleNotification(Notification):
    """Сообщение с текстом и степенью срочности за ним.

    Attributes:
        _text: Текст, который увидит человек.
        _severity: Насколько сообщение срочное.
    """

    def __init__(self, text: str, severity: str = "info") -> None:
        """Инициализирует сообщение.

        Args:
            text: Текст, который увидит человек.
            severity: Насколько сообщение срочное.
        """
        self._text = text
        self._severity = severity

    @property
    def text(self) -> str:
        """Возвращает сообщение таким, каким оно доходит до человека."""
        return self._text

    @property
    def severity(self) -> str:
        """Возвращает срочность сообщения."""
        return self._severity


class NotificationFactoryImpl:
    """Строит формулировки всех сообщений, которые может получить человек.

    Прикладной слой просит сообщение по имени, поэтому формулировки системы
    решаются в одном месте, а не расползаются по сценариям.
    """

    def board_online(self) -> Notification:
        """Возвращает сообщение о вернувшейся плате."""
        return SimpleNotification("Плата снова на связи.")

    def board_offline(self) -> Notification:
        """Возвращает сообщение пропавшей плате."""
        return SimpleNotification("Плата потеряла связь.", "warning")

    def scenario_started(self, scenario_id: str, target: str | None) -> Notification:
        """Возвращает сообщение о начавшем действовать сценарии.

        Args:
            scenario_id: Идентификатор сценария.
            target: Место или предмет, который назвал человек.

        Returns:
            Notification: Сообщение для доставки.
        """
        del scenario_id
        subject = f" для «{target}»" if target else ""
        return SimpleNotification(f"Сценарий{subject} начал работу.")

    def scenario_progress(self, scenario_id: str, temperature: float | None) -> Notification:
        """Возвращает периодическое сообщение действующего сценария.

        Args:
            scenario_id: Идентификатор сценария.
            temperature: Текущая температура или None.

        Returns:
            Notification: Сообщение для доставки.
        """
        del scenario_id
        if temperature is None:
            return SimpleNotification("Сценарий выполняется, температура неизвестна.")
        return SimpleNotification(f"Сценарий выполняется, сейчас {temperature:.1f} °C.")

    def scenario_finished(self, scenario_id: str, reason: str) -> Notification:
        """Возвращает сообщение о дошедшем до конца сценарии.

        Args:
            scenario_id: Идентификатор сценария.
            reason: Почему сценарий дошёл до этого этапа.

        Returns:
            Notification: Сообщение для доставки.
        """
        del scenario_id, reason
        return SimpleNotification("Сценарий завершён.")

    def scenario_failed(self, scenario_id: str, reason: str) -> Notification:
        """Возвращает сообщение о сценарии, который не удалось выполнить.

        Args:
            scenario_id: Идентификатор сценария.
            reason: Почему не удалось.

        Returns:
            Notification: Сообщение для доставки.
        """
        del scenario_id, reason
        return SimpleNotification("Сценарий не удалось выполнить.", "warning")


class CommandReplyComposer:
    """Превращает структурный результат команды во фразу.

    Прикладной слой сообщает *что* случилось, а этот класс решает *как* об этом
    сказать. Разделённые, они могут быть и напечатаны в чате, и нарисованы в
    браузере — без двух копий формулировки, которые рано или поздно разойдутся.
    """

    def for_result(self, result: object) -> str:
        """Возвращает фразу о том, что дала команда.

        Args:
            result: Структурный результат выполненной команды.

        Returns:
            str: Фраза для человека.
        """
        if not isinstance(result, CommandReply):
            return str(result)
        details = result.details
        match result.intent:
            case Intent.SWITCH_DEVICE:
                return COMMAND_DEVICE_STATE.format(
                    device=details.get("device"), state=self._status(details.get("status"))
                )
            case Intent.SWITCH_ALL:
                devices = details.get("devices")
                if not isinstance(devices, (list, tuple)) or not devices:
                    return COMMAND_NOTHING_TO_SWITCH
                names = ", ".join(str(name) for name in devices)
                failed = details.get("failed")
                if isinstance(failed, (list, tuple)) and failed:
                    return COMMAND_SWITCHED_PARTIAL.format(
                        devices=names, failed=", ".join(str(name) for name in failed)
                    )
                return COMMAND_SWITCHED + names + "."
            case Intent.SET_TEMPERATURE:
                return COMMAND_TARGET_TEMPERATURE.format(
                    value=self._number(details.get("temperature"))
                )
            case Intent.SET_HUMIDITY:
                return COMMAND_TARGET_HUMIDITY.format(value=self._number(details.get("humidity")))
            case Intent.RUN_CAPABILITY:
                return COMMAND_CAPABILITY_DONE.format(device=details.get("device"))
            case Intent.DESCRIBE_HOME:
                return self._describe(details)
            case Intent.READ_TEMPERATURE:
                value = details.get("temperature")
                return (
                    COMMAND_NO_DATA
                    if value is None
                    else COMMAND_NOW_TEMPERATURE.format(value=self._number(value))
                )
            case Intent.READ_HUMIDITY:
                value = details.get("humidity")
                return (
                    COMMAND_NO_DATA
                    if value is None
                    else COMMAND_NOW_HUMIDITY.format(value=self._number(value))
                )
            case Intent.SCHEDULE_SCENARIO:
                start_at = details.get("start_at")
                return (
                    COMMAND_SCENARIO_STARTED.format(start_at=start_at) if start_at else COMMAND_DONE
                )
            case Intent.CANCEL_SCENARIO:
                return COMMAND_SCENARIO_CANCELLED
        return COMMAND_DONE

    def _describe(self, details: dict[str, object]) -> str:
        """Возвращает фразу о состоянии дома по показаниям и устройствам."""
        temperature = details.get("temperature")
        humidity = details.get("humidity")
        if temperature is None and humidity is None:
            return COMMAND_NO_DATA
        if humidity is None:
            return COMMAND_NOW_TEMPERATURE.format(value=self._number(temperature))
        if temperature is None:
            return COMMAND_NOW_HUMIDITY.format(value=self._number(humidity))
        return COMMAND_CLIMATE.format(
            temperature=float(str(temperature)), humidity=float(str(humidity))
        )

    @staticmethod
    def _status(raw: object) -> str:
        """Возвращает русское название положения контакта."""
        return STATUS_ON if raw == "ON" else STATUS_OFF

    @staticmethod
    def _number(raw: object) -> str:
        """Возвращает число в виде, пригодном для фразы, или «неизвестно»."""
        try:
            return f"{float(str(raw)):.1f}".removesuffix(".0")
        except (TypeError, ValueError):
            return UNKNOWN_VALUE
