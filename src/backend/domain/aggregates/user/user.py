"""Аккаунт человека.

Агрегат владеет правилами о том, каким аккаунт может быть. Хешированием он не владеет:
это криптография, она живёт в инфраструктуре за интерфейсом, а агрегат только хранит
переданную ему строку результата.

Регистрация аккаунта — тот же момент, когда остальной дом должен появиться, поэтому
агрегат записывает этот факт и позволяет подписанному обустраивать дом.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Self

from backend.domain.events import UserRegistered
from backend.domain.exceptions import WeakPasswordError
from backend.domain.identifiers import UserId
from backend.domain.value_objects.account.display_name import DisplayName
from backend.domain.value_objects.account.email import Email

MIN_PASSWORD_LENGTH = 8


@dataclass(frozen=True, slots=True)
class User:
    """Один человек, пользующийся платформой.

    Attributes:
        id: Идентификатор аккаунта.
        email: Логин аккаунта.
        password_hash: Сохранённая форма пароля, построенная хешером и никогда не
            разбираемая моделью.
        display_name: Имя, показанное в интерфейсе.
        created_at: Момент создания аккаунта.
        _events: Факты, записанные с момента загрузки аккаунта.
    """

    id: UserId
    email: Email
    password_hash: str
    display_name: DisplayName
    created_at: datetime
    _events: list[UserRegistered] = field(default_factory=list, repr=False, compare=False)

    @property
    def can_authenticate_with(self) -> str:
        """Возвращает сохранённый пароль, с которым сверят предъявленный.

        Агрегат отдаёт значение, а не сравнивает сам: хеширование — работа
        инфраструктуры, и модель отказывается обрастать зависимостью от криптографии.

        Returns:
            str: Сохранённая форма пароля.
        """
        return self.password_hash

    def pull_events(self) -> tuple[UserRegistered, ...]:
        """Возвращает записанные факты и забывает их.

        Returns:
            tuple[UserRegistered, ...]: Факты с прошлого обращения.
        """
        recorded = tuple(self._events)
        object.__setattr__(self, "_events", [])
        return recorded

    @classmethod
    def register(
        cls,
        email: Email,
        display_name: DisplayName,
        password_hash: str,
        password_length: int,
        created_at: datetime,
    ) -> Self:
        """Создаёт новый аккаунт.

        Args:
            email: Логин аккаунта.
            display_name: Имя, показанное в интерфейсе.
            password_hash: Сохранённая форма пароля.
            password_length: Длина пароля, который выбрал человек, — слишком
                короткую модель не примет.
            created_at: Момент создания аккаунта.

        Returns:
            Self: Созданный аккаунт.

        Raises:
            WeakPasswordError: Когда пароль короче разрешённого.
        """
        if password_length < MIN_PASSWORD_LENGTH:
            raise WeakPasswordError(MIN_PASSWORD_LENGTH)
        user = cls(
            id=UserId.generate(),
            email=email,
            password_hash=password_hash,
            display_name=display_name,
            created_at=created_at,
        )
        user._events.append(UserRegistered(user_id=user.id))
        return user
