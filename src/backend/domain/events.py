"""События домена.

Сущность, которая изменила что-то достойное рассказа, записывает факт вместо звонка
нотификатору. Прикладной слой собирает эти записи после коммита транзакции и отдаёт их
тому, кто подписан, — поэтому модель не знает ни про инфраструктуру сообщений, ни про
то, кто на них слушает.

Событие — простое незменяемое утверждение о том, что уже случилось. Ни отметки времени,
ни данных доставки в нём нет: момент ставит издатель, потому что только он знает, когда
факт стал виден вне транзакции.

Подписчик получает набор фактов одного прерывания транзакции, и типы в нём разные,
поэтому союз `DomainEvent` называет всё, что вообще может лежать в таком наборе: раздатчик
и подписчики говорят о фактах домена, а не о произвольных объектах.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.domain.identifiers import DeviceId, EspDeviceId, ScenarioId, UserId


class EventName:
    """Имена событий, которые читают подписчики realtime-канала.

    Одно событие получает одно имя и звучит ровно так, как записано здесь: файл,
    где перечислены все имена, заменяет константы, продублированные в десятке
    модулей приложения.
    """

    BOARD_ONLINE = "board.online"
    BOARD_OFFLINE = "board.offline"
    BOARD_ERROR = "board.error"
    BOARD_PAIRED = "board.paired"
    BOARD_NETWORK_CHANGED = "board.network_changed"
    BOARD_RELAY_CHANGED = "board.relay_changed"
    BOARD_ANNOUNCEMENT_PUBLISHED = "board.announcement_published"
    DEVICES_UPDATED = "devices.updated"
    DEVICE_STATE_CHANGED = "device.state_changed"
    AUTOMATION_UPDATED = "automation.updated"
    SCENARIO_SCHEDULED = "scenario.scheduled"
    SCENARIO_STARTED = "scenario.started"
    SCENARIO_FINISHED = "scenario.finished"
    SENSOR_TEMPERATURE_CHANGED = "sensor.temperature_changed"
    SENSOR_HUMIDITY_CHANGED = "sensor.humidity_changed"


@dataclass(frozen=True, slots=True)
class UserRegistered:
    """Новый аккаунт существует, и его дом надо обустраивать.

    Attributes:
        user_id: Идентификатор нового аккаунта.
    """

    user_id: UserId


@dataclass(frozen=True, slots=True)
class DeviceConfigured:
    """Настройка логического устройства изменилась.

    Attributes:
        user_id: Владелец устройства.
        device_id: Идентификатор изменённого устройства.
    """

    user_id: UserId
    device_id: DeviceId


@dataclass(frozen=True, slots=True)
class DeviceCapabilityApplied:
    """Способность дошла до железа по просьбе аккаунта.

    Только здесь записано правило «ручное действие ставит автоматику на паузу», а не
    строкой в конце каждого сценария, который что-нибудь переключает.

    Attributes:
        user_id: Владелец устройства.
        device_id: Идентификатор устройства.
        device_name: Имя, показанное человеку.
        channel: Физический канал реле, который переключили.
        capability: Выполненная способность.
        manual: Просил ли человек сам, в отличие от автоматики или сценария.
    """

    user_id: UserId
    device_id: DeviceId
    device_name: str
    channel: int
    capability: str
    manual: bool


@dataclass(frozen=True, slots=True)
class AutomationSettingsChanged:
    """Настройка автоматизации аккаунта изменилась.

    Attributes:
        user_id: Владелец настройки.
    """

    user_id: UserId


@dataclass(frozen=True, slots=True)
class ScenarioScheduled:
    """Сценарий сохранён и ждёт своего момента начать.

    Attributes:
        user_id: Владелец сценария.
        scenario_id: Идентификатор сценария.
    """

    user_id: UserId
    scenario_id: ScenarioId


@dataclass(frozen=True, slots=True)
class ScenarioStarted:
    """Сценарий начал действовать в доме.

    Attributes:
        user_id: Владелец сценария.
        scenario_id: Идентификатор сценария.
    """

    user_id: UserId
    scenario_id: ScenarioId


@dataclass(frozen=True, slots=True)
class ScenarioFinished:
    """Сценарий дошёл до итогового этапа.

    Attributes:
        user_id: Владелец сценария.
        scenario_id: Идентификатор сценария.
        status: Этап, которого сценарий достиг.
        reason: Почему он его достиг.
    """

    user_id: UserId
    scenario_id: ScenarioId
    status: str
    reason: str


@dataclass(frozen=True, slots=True)
class BoardPaired:
    """Плата стала принадлежать аккаунту.

    Attributes:
        user_id: Владелец платы.
        board_id: Идентификатор платы.
    """

    user_id: UserId
    board_id: EspDeviceId


@dataclass(frozen=True, slots=True)
class BoardAnnouncementPublished:
    """Плата, у которой пока нет хозяина, просит, чтобы её забрали.

    Attributes:
        label: Короткий код, который интерфейс показывает рядом с платой.
    """

    label: str = field(compare=False)


DomainEvent = (
    UserRegistered
    | DeviceConfigured
    | DeviceCapabilityApplied
    | AutomationSettingsChanged
    | ScenarioScheduled
    | ScenarioStarted
    | ScenarioFinished
    | BoardPaired
    | BoardAnnouncementPublished
)
