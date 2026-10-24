"""Протокол, который говорят бэкенд и плата по сокету.

Каждый кадр — модель Pydantic, и на приёме, и на отправке. Входящие кадры
объединены в дискриминированное множество, поэтому кадр кривой, обрезанный или
написанный прошивкой, которая говорит то, о чём с сервером не договаривались,
отвергается с ошибкой, называющей сломанное поле, а не превращается в мешок
необязательных None, от которого потом защищается вся остальная система.

Четвёртая версия убирает из протокола звук: распознавания речи в развёртывании
нет, поэтому микрофон, окно записи и уровень громкости перестали быть частью
договора сторон.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

PROTOCOL_VERSION = 4
"""Версия, которую описывают и прошивка, и документация протокола."""


class MalformedFrameError(ValueError):
    """Кадр протокола не удалось прочитать.

    Args:
        message: На что указала проверка.
    """

    def __init__(self, message: str) -> None:
        """Инициализирует отказ.

        Args:
            message: На что проверка указала.
        """
        super().__init__(f"malformed board frame: {message}")


class _Inbound(BaseModel):
    """Общее поведение каждого кадра, пришедшего от платы."""

    model_config = ConfigDict(extra="allow", populate_by_name=True, frozen=True)


class HelloFrame(_Inbound):
    """Handshake платы, которая только что дозвонилась.

    Attributes:
        type: Разделитель объединения.
        pairing_key: Секрет, который предъявляет плата; отсутствует у переподключившейся
            платы, чей хозяин ей уже известен.
        label: Короткий код, который плата сообщила о себе.
        firmware_version: Версия прошивки, которую сообщила плата.
        ssid: Имя сети, в которой находится плата; отсутствует вне сети.
        provisioned: Есть ли у платы уже собственная сеть.
    """

    type: Literal["HELLO"] = "HELLO"
    pairing_key: str | None = None
    label: str = ""
    firmware_version: str = ""
    ssid: str | None = None
    provisioned: bool = False


class StateFrame(_Inbound):
    """Всё, что знает плата: контакты и датчики.

    Attributes:
        type: Разделитель объединения.
        relays: Положения контактов по порядку каналов, начиная с первого.
        temperature: Измеренная температура; отсутствует, когда датчик не ответил.
        humidity: Измеренная относительная влажность; отсутствует, когда датчик
            не ответил.
    """

    type: Literal["STATE"] = "STATE"
    relays: list[bool] = Field(default_factory=list)
    temperature: float | None = None
    humidity: float | None = None


class SensorDataFrame(_Inbound):
    """Показания датчиков климата, без всего остального.

    Attributes:
        type: Разделитель объединения.
        temperature: Измеренная температура; отсутствует, когда датчик не ответил.
        humidity: Измеренная относительная влажность; отсутствует, когда датчик
            не ответил.
    """

    type: Literal["SENSOR_DATA"] = "SENSOR_DATA"
    temperature: float | None = None
    humidity: float | None = None


class AckFrame(_Inbound):
    """Подтверждение одной команды.

    Attributes:
        type: Разделитель объединения.
        command_id: Идентификатор подтверждённой команды.
    """

    type: Literal["ACK"] = "ACK"
    command_id: str


class ErrorFrame(_Inbound):
    """Отказ, о котором сообщает сама плата.

    Attributes:
        type: Разделитель объединения.
        code: Машинночитаемый код отказа.
        message: Описание отказа человеческими словами.
    """

    type: Literal["ERROR"] = "ERROR"
    code: str
    message: str = ""


type InboundFrame = Annotated[
    HelloFrame | StateFrame | SensorDataFrame | AckFrame | ErrorFrame,
    Field(discriminator="type"),
]

INBOUND_ADAPTER: TypeAdapter[InboundFrame] = TypeAdapter(InboundFrame)


class OutboundFrame(BaseModel):
    """Общее поведение каждого кадра, отправляемого плате."""

    model_config = ConfigDict(frozen=True)

    def to_json(self) -> str:
        """Сериализует кадр.

        Returns:
            str: JSON-документ, записанный в сокет.
        """
        return self.model_dump_json()


class SetRelayFrame(OutboundFrame):
    """Переключает один контакт реле.

    Attributes:
        type: Тип кадра.
        command_id: Идентификатор, по которому ждут подтверждения.
        channel: Физический канал реле, начиная с первого.
        state: True замыкает контакт, False размыкает.
    """

    type: Literal["SET_RELAY"] = "SET_RELAY"
    command_id: str
    channel: int = Field(ge=1)
    state: bool


class GetStateFrame(OutboundFrame):
    """Просит плату прислать заново всё, что она знает.

    Attributes:
        type: Тип кадра.
    """

    type: Literal["GET_STATE"] = "GET_STATE"


class ClaimFrame(OutboundFrame):
    """Сообщает плате без хозяина, что её поняли.

    Аккаунт выбирают в интерфейсе того, кто держит плату в руках, поэтому плате
    не говорят, кому именно она досталась.

    Attributes:
        type: Тип кадра.
        label: Короткий код, который интерфейс показывает рядом с платой.
        ttl_sec: Сколько времени предложение остаётся действительным.
    """

    type: Literal["CLAIM"] = "CLAIM"
    label: str
    ttl_sec: int = Field(ge=1)


class ClaimedFrame(OutboundFrame):
    """Сообщает плате, что она принадлежит аккаунту.

    Кадр шлют при каждом успешном handshake нарочно: плата, пропустившая момент
    забирания, узнаёт об этом всё равно, а получить сообщение дважды для неё ничего
    не стоит.

    Attributes:
        type: Тип кадра.
    """

    type: Literal["CLAIMED"] = "CLAIMED"


class RejectedFrame(OutboundFrame):
    """Отказывает плате, которой вход не разрешён.

    Attributes:
        type: Тип кадра.
        reason: Машинночитаемая причина отказа.
    """

    type: Literal["REJECTED"] = "REJECTED"
    reason: str


class SetNetworkFrame(OutboundFrame):
    """Сообщает плате сеть, которую та должна использовать.

    Плата пишет настройки в свою память и переподключается, поэтому изменение
    переживает перезапуск питания. Пароль едет только в этом кадре: на сервере он не
    хранится и обратно с сервера не уходит.

    Attributes:
        type: Тип кадра.
        command_id: Идентификатор, по которому ждут подтверждения.
        ssid: Имя беспроводной сети.
        password: Пароль этой сети; пустой, когда сеть открыта.
        host: Адрес сервера, которому плата докладывается.
        server_port: Порт обычного интерфейса этого сервера.
        socket_port: Порт доски этого сервера.
        socket_path: Путь доски этого сервера.
    """

    type: Literal["SET_NETWORK"] = "SET_NETWORK"
    command_id: str
    ssid: str = Field(min_length=1, max_length=32)
    password: str = Field(default="", max_length=64)
    host: str = Field(min_length=1, max_length=64)
    server_port: int = Field(ge=1, le=65535)
    socket_port: int = Field(ge=1, le=65535)
    socket_path: str = Field(min_length=1, max_length=64)


def parse_inbound(raw: str | bytes) -> InboundFrame:
    """Читает один кадр, пришедший от платы.

    Args:
        raw: Кадр таким, каким он пришёл в сокет.

    Returns:
        InboundFrame: Проверенный кадр.

    Raises:
        MalformedFrameError: Когда кадр не является правильным кадром протокола.
    """
    text = raw.decode("utf-8", "replace") if isinstance(raw, bytes | bytearray) else raw
    try:
        return INBOUND_ADAPTER.validate_json(text)
    except ValueError as error:
        raise MalformedFrameError(str(error)) from error
