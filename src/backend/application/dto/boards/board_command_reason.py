"""Причины, по которым команда платы не исполнилась.

Эти слова ходят по шине между процессами: отправитель команды и её исполнитель
обязаны называть один и тот же отказ одинаково. Пока литералы лежали в двух
адаптерах порознь, первое же переименование развело бы их молча — отправитель искал
бы причину, которую никто больше не пишет.
"""

from __future__ import annotations

from enum import StrEnum


class BoardCommandReason(StrEnum):
    """Машинная причина отказа команды плате.

    Attributes:
        OFFLINE: Плата не держит соединения с этим процессом.
        ACK_TIMEOUT: Плата не подтвердила команду за отведённое время.
        DELIVERY_FAILED: Кадр не удалось передать либо ответ не разобрался.
        INVALID_NETWORK: Команда смены сети пришла без годного профиля.
        SECRET_MISSING: Секрет команды не нашёлся в хранилище.
        UNKNOWN_COMMAND: Исполнитель не знает такого рода команды.
        BOARD_NOT_CHOSEN: Устройство не привязано к плате, а плат в доме несколько.
    """

    OFFLINE = "esp_offline"
    ACK_TIMEOUT = "ack_timeout"
    DELIVERY_FAILED = "esp_delivery_failed"
    INVALID_NETWORK = "invalid_network"
    SECRET_MISSING = "network_secret_missing"
    UNKNOWN_COMMAND = "unknown_command"
    BOARD_NOT_CHOSEN = "board_not_chosen"
