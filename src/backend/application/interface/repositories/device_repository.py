"""Хранилище логических устройств одного аккаунта.

Каждая операция ограничена владельцем, поэтому вызывающий не может достать чужое
устройство, даже угадав его идентификатор.
"""

from __future__ import annotations

from backend.application.interface.repositories.base import CrudRepository
from backend.domain.aggregates.device.device import Device
from backend.domain.identifiers import DeviceId


class DeviceRepository(CrudRepository[Device, DeviceId]):
    """Полный набор операций над устройствами аккаунта."""
