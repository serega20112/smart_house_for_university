"""Отказы аккаунта и его учётных данных."""

from __future__ import annotations

from backend.domain.exceptions.base import DomainError


class InvalidEmailError(DomainError):
    """Логин не похож на адрес почты.

    Attributes:
        reason: Почему значение отвергнуто.
    """

    def __init__(self, reason: str = "value is not a valid email address") -> None:
        """Запоминает причину отказа.

        Args:
            reason: Почему значение отвергнуто.
        """
        super().__init__(f"Email {reason}")
        self.reason = reason


class InvalidDisplayNameError(DomainError):
    """Отображаемое имя пусто или не помещается в экранный размер.

    Attributes:
        reason: Почему значение отвергнуто.
    """

    def __init__(self, reason: str = "value is empty or too long") -> None:
        """Запоминает причину отказа.

        Args:
            reason: Почему значение отвергнуто.
        """
        super().__init__(f"Display name {reason}")
        self.reason = reason


class WeakPasswordError(DomainError):
    """Пароль короче минимума, который принимает модель.

    Attributes:
        minimum: Минимальная допустимая длина.
    """

    def __init__(self, minimum: int) -> None:
        """Запоминает требуемый минимум.

        Args:
            minimum: Минимальная допустимая длина.
        """
        super().__init__(f"Password must be at least {minimum} characters long")
        self.minimum = minimum
