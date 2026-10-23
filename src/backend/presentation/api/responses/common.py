"""Общие тела ответов: служебные исходы и доступность сервиса."""

from __future__ import annotations

from backend.presentation.api.base import StrictModel


class OperationResponse(StrictModel):
    """Ответ операции, которая изменила один признак или ничего.

    Attributes:
        status: Название исхода.
        message: Фраза, которую видит человек.
    """

    status: str
    message: str


class HealthResponse(StrictModel):
    """Доступность сервиса.

    Attributes:
        status: Доступность сервиса.
        name: Название развёртывания.
        version: Версия запущенной сборки.
    """

    status: str
    name: str
    version: str
