"""Отказы плат и их сети."""

from __future__ import annotations

from backend.domain.exceptions.base import DomainError


class InvalidBoardNameError(DomainError):
    """Имя платы пусто или не помещается на экран.

    Attributes:
        reason: Почему значение отвергнуто.
    """

    def __init__(self, reason: str = "value is empty or too long") -> None:
        """Запоминает причину отказа.

        Args:
            reason: Почему значение отвергнуто.
        """
        super().__init__(f"Board name {reason}")
        self.reason = reason


class InvalidPairingKeyError(DomainError):
    """Ключ сопряжения пуст или имеет неподходящий вид.

    Attributes:
        reason: Почему значение отвергнуто.
    """

    def __init__(self, reason: str = "value is empty or malformed") -> None:
        """Запоминает причину отказа.

        Args:
            reason: Почему значение отвергнуто.
        """
        super().__init__(f"Pairing key {reason}")
        self.reason = reason


class InvalidNetworkProfileError(DomainError):
    """Сеть платы нельзя применить в том виде, в каком её дали.

    Attributes:
        reason: Почему значения отвергнуты.
    """

    def __init__(self, reason: str) -> None:
        """Запоминает причину отказа.

        Args:
            reason: Почему значения отвергнуты.
        """
        super().__init__(f"Network profile {reason}")
        self.reason = reason


class ClaimExpiredError(DomainError):
    """Окно, в котором плату можно было забрать, закрылось."""

    def __init__(self) -> None:
        """Объясняет, что предложение больше не действительно."""
        super().__init__(
            "this board announcement is no longer valid, ask the board to announce again"
        )


class ClaimAlreadyTakenError(DomainError):
    """Плату раньше забрал другой аккаунт."""

    def __init__(self) -> None:
        """Объясняет, что плата уже принадлежит кому-то другому."""
        super().__init__("this board is already owned by another account")
