"""То, что человек набрал, чтобы создать аккаунт."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RegisterAccountCommand:
    """Новый аккаунт, который попросили создать интерфейс.

    Attributes:
        email: Логин, который выбрал человек.
        display_name: Имя, под которым к нему хотят обращаться.
        password: Пароль в открытом виде; дальше этого объекта он не уходит.
    """

    email: str
    display_name: str
    password: str
