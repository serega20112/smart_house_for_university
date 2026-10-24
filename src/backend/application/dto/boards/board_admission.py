"""Разговор платы с сервером до того, как ей отдана хоть одна команда.

Greeting — то, что плата сообщает о себе, а ответ сервера — одно из трёх: владельца
нашли, плату узнали и ждут её хозяина, либо ключ не известен вовсе. Решения принимает
прикладной слой, поэтому транспорт оперирует этими значениями, а не строками протокола.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.domain.identifiers import EspDeviceId, UserId


@dataclass(frozen=True, slots=True)
class BoardGreeting:
    """Первое сообщение платы.

    Attributes:
        pairing_key: Секрет, который плата предъявляет, или None, если она его не
            назвала.
        label: Короткий код о себе, который сообщила плата, возможно пустой.
        firmware: Версия прошивки, названная самой платой.
        ssid: Сеть, в которой плата сейчас, или None, если она вне сети.
        provisioned: Знает ли плата вообще какую-нибудь сеть.
        claims_owned: Считает ли плата, что хозяин у неё уже есть.
        server_host: Адрес сервера, которому плата докладывает, или None, если она
            его не сообщила.
        server_port: Порт интерфейса этого сервера; 0, если не сообщён.
        socket_port: Порт сокета плат этого сервера; 0, если не сообщён.
        socket_path: Путь сокета плат этого сервера, или None, если не сообщён.
    """

    pairing_key: str | None
    label: str = ""
    firmware: str = ""
    ssid: str | None = None
    provisioned: bool = False
    claims_owned: bool = False
    server_host: str | None = None
    server_port: int = 0
    socket_port: int = 0
    socket_path: str | None = None


@dataclass(frozen=True, slots=True)
class BoardOwner:
    """Плата принадлежит аккаунту, и соединение можно продолжать.

    Attributes:
        user_id: Владелец платы и дома, который она питает.
        board_id: Идентификатор сопряжённой платы.
    """

    user_id: UserId
    board_id: EspDeviceId


@dataclass(frozen=True, slots=True)
class BoardOffer:
    """Плата объявлена и ждёт, пока её заберут из интерфейса.

    Attributes:
        label: Короткий код, который интерфейс показывает рядом с платой.
        ttl_sec: Сколько секунд предложение остаётся действительным.
    """

    label: str
    ttl_sec: int


@dataclass(frozen=True, slots=True)
class BoardRefusal:
    """Плате не разрешено соединение.

    Attributes:
        reason: Машинночитаемая причина отказа.
    """

    reason: str


BoardAdmission = BoardOwner | BoardOffer | BoardRefusal
