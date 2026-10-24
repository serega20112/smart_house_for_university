"""Авторизует уже существующий аккаунт.

Чтение идёт через интерфейс чтения, а не через транзакцию: авторизовать кого-то — это
select, а select, завёрнутый в транзакцию, — пустая нагрузка.
"""

from __future__ import annotations

from backend.application.dto.account.authenticate_command import AuthenticateCommand
from backend.application.errors import InvalidCredentialsError
from backend.application.interfaces.queries.account_queries import AccountQueries
from backend.application.interfaces.services.security.password_hasher import PasswordHasher
from backend.application.interfaces.services.security.session_token_issuer import SessionTokenIssuer
from backend.application.use_cases.accounts.result import AuthenticatedSession
from backend.domain.exceptions import InvalidEmailError
from backend.domain.value_objects.account.email import Email


class AuthenticateAccountUseCase:
    """Проверяет логин с паролем и выдаёт токен сессии."""

    def __init__(
        self,
        queries: AccountQueries,
        hasher: PasswordHasher,
        tokens: SessionTokenIssuer,
    ) -> None:
        """Инициализирует сценарий.

        Args:
            queries: Дешёвые чтения аккаунтов.
            hasher: Сверяет пароль в открытом виде с сохранённым.
            tokens: Выдаёт токен сессии.
        """
        self._queries = queries
        self._hasher = hasher
        self._tokens = tokens

    async def execute(self, command: AuthenticateCommand) -> AuthenticatedSession:
        """Авторизует аккаунт и открывает для него сессию.

        Неизвестный логин и неверный пароль дают ровно один и тот же отказ, чтобы
        ответ никогда не выдавал, существует ли аккаунт. Сверка пароля выполняется
        и тогда, когда записи нет: иначе быстрый ответ сам стал бы ответом.

        Args:
            command: Учётные данные, предъявленные при входе.

        Returns:
            AuthenticatedSession: Профиль и токен сессии.

        Raises:
            InvalidCredentialsError: Когда логин или пароль неверны.
        """
        try:
            email = Email.parse(command.email)
        except InvalidEmailError as error:
            raise InvalidCredentialsError() from error
        record = await self._queries.get_auth_record(email.value)
        stored = None if record is None else record.password_hash
        verified = await self._hasher.verify(command.password, stored)
        if record is None or not verified:
            raise InvalidCredentialsError()
        session = self._tokens.issue(record.user_id)
        return AuthenticatedSession(
            profile=record.profile(),
            token=session.token,
            expires_at=session.expires_at,
        )
