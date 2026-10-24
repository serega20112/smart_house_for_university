"""Учётные данные, предъявленные при входе."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthenticateCommand:
    """Учётные данные, которыми человек представляется, входя.

    Attributes:
        email: Логин аккаунта.
        password: Пароль в открытом виде.
    """

    email: str
    password: str
