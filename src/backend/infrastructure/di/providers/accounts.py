"""Аккаунты: регистрация и вход."""

from __future__ import annotations

from dishka import Provider, Scope, provide

from backend.application.interface.queries.account_queries import AccountQueries
from backend.application.interface.services.clock import Clock
from backend.application.interface.services.password_hasher import PasswordHasher
from backend.application.interface.services.session_token_issuer import SessionTokenIssuer
from backend.application.interface.unit_of_work.account import AccountUnitOfWorkFactory
from backend.application.services.reaction_dispatcher import ReactionDispatcher
from backend.application.use_cases.accounts.authenticate_account import AuthenticateAccountUseCase
from backend.application.use_cases.accounts.register_account import RegisterAccountUseCase

REQUEST = Scope.REQUEST


class AccountProvider(Provider):
    """Создание аккаунта и вход в него."""

    @provide(scope=REQUEST)
    def register_account(
        self,
        uow: AccountUnitOfWorkFactory,
        hasher: PasswordHasher,
        tokens: SessionTokenIssuer,
        reactions: ReactionDispatcher,
        clock: Clock,
    ) -> RegisterAccountUseCase:
        """Собирает создание аккаунта."""
        return RegisterAccountUseCase(uow, hasher, tokens, reactions, clock)

    @provide(scope=REQUEST)
    def authenticate_account(
        self,
        queries: AccountQueries,
        hasher: PasswordHasher,
        tokens: SessionTokenIssuer,
    ) -> AuthenticateAccountUseCase:
        """Собирает вход в аккаунт."""
        return AuthenticateAccountUseCase(queries, hasher, tokens)
