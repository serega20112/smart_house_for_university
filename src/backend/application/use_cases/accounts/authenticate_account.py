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
from backend.domain.identifiers import UserId
from backend.domain.value_objects.account.account_profile import AccountProfile
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
        ответ никогда не выдавал, существует ли аккаунт.

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
        stored = await self._queries.get_credentials(email.value)
        if stored is None or not self._hasher.verify(command.password, stored.password_hash):
            raise InvalidCredentialsError()
        session = self._tokens.issue(stored.user_id)
        return AuthenticatedSession(
            profile=await self._profile_of(stored.user_id),
            token=session.token,
            expires_at=session.expires_at,
        )

    async def _profile_of(self, user_id: UserId) -> AccountProfile:
        profile = await self._queries.get_profile(user_id)
        if profile is None:
            raise InvalidCredentialsError()
        return profile
