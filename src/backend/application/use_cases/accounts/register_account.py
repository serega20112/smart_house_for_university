"""Register a new account.

A new account is not an empty row. It gets its identifier, its home, its devices
and a dashboard, so the very first request already returns a complete personalized
projection.

This use case does not know any of that. It creates the account, which records the
fact that it exists, and hands that fact to the dispatcher. Whatever cares about
new accounts does the rest, and a second module that needs to welcome new users
subscribes without touching this file.
"""

from __future__ import annotations

from backend.application.dto.account.register_account_command import RegisterAccountCommand
from backend.application.interface.services.clock import Clock
from backend.application.interface.services.domain_event_dispatcher import DomainEventDispatcher
from backend.application.interface.services.password_hasher import PasswordHasher
from backend.application.interface.services.session_token_issuer import SessionTokenIssuer
from backend.application.interface.unit_of_work.account import AccountUnitOfWorkFactory
from backend.application.use_cases.accounts.result import AuthenticatedSession
from backend.domain.aggregates.user.user import User
from backend.domain.value_objects.account.account_profile import AccountProfile
from backend.domain.value_objects.account.display_name import DisplayName
from backend.domain.value_objects.account.email import Email


class RegisterAccountUseCase:
    """Creates an account and opens a session for it."""

    def __init__(
        self,
        account_uow: AccountUnitOfWorkFactory,
        hasher: PasswordHasher,
        tokens: SessionTokenIssuer,
        dispatcher: DomainEventDispatcher,
        clock: Clock,
    ) -> None:
        """Initialize the use case.

        Args:
            account_uow: Factory producing transactions over the accounts.
            hasher: Turns a plain password into a stored form.
            tokens: Issues the session token.
            dispatcher: Announces the fact that the account exists.
            clock: Source of the current time.

        Returns:
            None.
        """
        self._account_uow = account_uow
        self._hasher = hasher
        self._tokens = tokens
        self._dispatcher = dispatcher
        self._clock = clock

    async def execute(self, command: RegisterAccountCommand) -> AuthenticatedSession:
        """Create the account and open a session for it.

        Args:
            command: What the person typed.

        Returns:
            AuthenticatedSession: Profile and session token.

        Raises:
            EmailAlreadyTakenError: When the login is already registered. The
            uniqueness is enforced by the store, so two simultaneous registrations
            cannot both succeed.
            InvalidEmailError: When the login is malformed.
            InvalidDisplayNameError: When the name is empty or too long.
            WeakPasswordError: When the password is too short.
        """
        user = User.register(
            email=Email.parse(command.email),
            display_name=DisplayName.parse(command.display_name),
            password_hash=self._hasher.hash(command.password),
            password_length=len(command.password),
            created_at=self._clock.now(),
        )
        async with self._account_uow() as uow:
            await uow.accounts.add(user)
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
