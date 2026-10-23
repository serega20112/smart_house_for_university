"""Контракты операций над аккаунтами."""

from backend.application.dto.account.authenticate_command import AuthenticateCommand
from backend.application.dto.account.register_account_command import RegisterAccountCommand

__all__ = ["AuthenticateCommand", "RegisterAccountCommand"]
