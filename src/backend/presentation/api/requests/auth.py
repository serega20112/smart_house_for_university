"""Тела запросов аккаунта и перевод их в команды приложения."""

from __future__ import annotations

from pydantic import Field

from backend.application.dto.account.authenticate_command import AuthenticateCommand
from backend.application.dto.account.register_account_command import RegisterAccountCommand
from backend.presentation.api.base import StrictModel

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 256
DISPLAY_NAME_MAX_LENGTH = 120


class RegisterBody(StrictModel):
    """Запрос на создание аккаунта.

    Attributes:
        email: Логин, который выбрал человек.
        display_name: Имя, под которым его будут звать.
        password: Пароль в открытом виде.
    """

    email: str
    display_name: str = Field(min_length=1, max_length=DISPLAY_NAME_MAX_LENGTH)
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)


class LoginBody(StrictModel):
    """Запрос на вход.

    Attributes:
        email: Логин аккаунта.
        password: Пароль в открытом виде.
    """

    email: str
    password: str


def register_command(body: RegisterBody) -> RegisterAccountCommand:
    """Возвращает команду создания аккаунта.

    Args:
        body: Тело запроса на создание.

    Returns:
        RegisterAccountCommand: Команда, понятная сценарию приложения.
    """
    return RegisterAccountCommand(
        email=body.email,
        display_name=body.display_name,
        password=body.password,
    )


def authenticate_command(body: LoginBody) -> AuthenticateCommand:
    """Возвращает команду входа.

    Args:
        body: Тело запроса на вход.

    Returns:
        AuthenticateCommand: Команда, понятная сценарию приложения.
    """
    return AuthenticateCommand(email=body.email, password=body.password)
