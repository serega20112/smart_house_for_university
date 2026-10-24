"""Регистрирует новый аккаунт.

Новый аккаунт — не пустая строка. Он получает идентификатор, свой дом, свои устройства и
панель, поэтому первый же запрос отдаёт законченную персональную проекцию.

Этот сценарий ничего из того не знает. Он создаёт аккаунт, тот записывает факт
собственного существования, и сценарий передаёт этот факт раздатчику. Остальное делает
тот, кого касаются новые аккаунты, а второй модуль, которому нужно приветствовать
вошедших, подписывается, не трогая этот файл.
"""

from __future__ import annotations

from backend.application.dto.account.register_account_command import RegisterAccountCommand
from backend.application.dto.views.account_profile import AccountProfile
from backend.application.interfaces.services.messaging.domain_event_dispatcher import (
    DomainEventDispatcher,
)
from backend.application.interfaces.services.security.password_hasher import PasswordHasher
from backend.application.interfaces.services.security.session_token_issuer import SessionTokenIssuer
from backend.application.interfaces.services.system.clock import Clock
from backend.application.interfaces.unit_of_work.account import AccountUnitOfWorkFactory
from backend.application.use_cases.accounts.result import AuthenticatedSession
from backend.domain.aggregates.user.user import User
from backend.domain.value_objects.account.display_name import DisplayName
from backend.domain.value_objects.account.email import Email
from backend.domain.value_objects.account.raw_password import RawPassword


class RegisterAccountUseCase:
    """Создаёт аккаунт и открывает для него сессию."""

    def __init__(
        self,
        account_uow: AccountUnitOfWorkFactory,
        hasher: PasswordHasher,
        tokens: SessionTokenIssuer,
        dispatcher: DomainEventDispatcher,
        clock: Clock,
    ) -> None:
        """Инициализирует сценарий.

        Args:
            account_uow: Фабрика транзакций над аккаунтами.
            hasher: Превращает пароль в открытом виде в сохраняемую форму.
            tokens: Выдаёт токен сессии.
            dispatcher: Объявляет факт существования аккаунта.
            clock: Источник текущего времени.
        """
        self._account_uow = account_uow
        self._hasher = hasher
        self._tokens = tokens
        self._dispatcher = dispatcher
        self._clock = clock

    async def execute(self, command: RegisterAccountCommand) -> AuthenticatedSession:
        """Создаёт аккаунт и открывает для него сессию.

        Args:
            command: То, что набрал человек.

        Returns:
            AuthenticatedSession: Профиль и токен сессии.

        Raises:
            EmailAlreadyTakenError: Когда логин уже зарегистрирован. За
                единственностью следит хранилище, поэтому две одновременные
                регистрации не пройдут обе.
            InvalidEmailError: Когда логин неподходящей формы.
            InvalidDisplayNameError: Когда имя пустое или слишком длинное.
            WeakPasswordError: Когда пароль слишком короткий.
        """
        raw_password = RawPassword(command.password)
        user = User.register(
            email=Email.parse(command.email),
            display_name=DisplayName.parse(command.display_name),
            password_hash=await self._hasher.hash(raw_password.value),
            created_at=self._clock.now(),
        )
        async with self._account_uow() as uow:
            await uow.accounts.add(user)
            await uow.commit()
        session = self._tokens.issue(user.id)
        await self._dispatcher.dispatch(user.pull_events())
        return AuthenticatedSession(
            profile=_profile_of(user),
            token=session.token,
            expires_at=session.expires_at,
        )


def _profile_of(user: User) -> AccountProfile:
    return AccountProfile(
        id=user.id,
        email=user.email.value,
        display_name=user.display_name.value,
        created_at=user.created_at,
    )
