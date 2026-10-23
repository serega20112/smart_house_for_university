"""Хеширование паролей.

Хранимая форма описывает себя сама: называет алгоритм, число повторов и соль, из
которой она получилась, поэтому стоимость можно поднять позже без переноса уже
записанных строк. Проверка сравнивает дайджесты за постоянное время.

bcrypt не выбран осознанно: он требует отдельной зависимости и обрезает пароль на
72 байтах, а PBKDF2-HMAC лежит в стандартной библиотеке. Хранимая форма начинается
с имени алгоритма, поэтому переход на bcrypt или argon2 остаётся шагом кода, а не
переносом данных: строки, записанные прежней веткой, продолжит проверять прежний
код.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from backend.application.interface.services.password_hasher import PasswordHasher

ALGORITHM_PREFIX = "pbkdf2"
DEFAULT_DIGEST = "sha256"
KEY_LENGTH_BYTES = 32
FIELD_SEPARATOR = "$"


class Pbkdf2PasswordHasher(PasswordHasher):
    """Выводит хранимые пароли через PBKDF2-HMAC.

    Args:
        iterations: Число витков одного вывода; стоит дороже линейно и касается
            только что записанных паролей.
        salt_bytes: Длина соли одного пароля.
        digest: Хеш, используемый внутри PBKDF2.

    Returns:
        None.
    """

    def __init__(
        self,
        iterations: int,
        salt_bytes: int,
        digest: str = DEFAULT_DIGEST,
    ) -> None:
        """Инициализирует хешер.

        Args:
            iterations: Число витков одного вывода.
            salt_bytes: Длина соли одного пароля.
            digest: Хеш, используемый внутри PBKDF2.

        Returns:
            None.
        """
        self._iterations = iterations
        self._salt_bytes = salt_bytes
        self._digest = digest

    def hash(self, password: str) -> str:
        """Производит хранимую форму пароля.

        Args:
            password: Пароль, который выбрал человек.

        Returns:
            str: Описывающая себя форма с солью и стоимостью.
        """
        salt = secrets.token_bytes(self._salt_bytes)
        digest = hashlib.pbkdf2_hmac(
            self._digest,
            password.encode("utf-8"),
            salt,
            self._iterations,
            dklen=KEY_LENGTH_BYTES,
        )
        return FIELD_SEPARATOR.join(
            (self._label, str(self._iterations), _encode(salt), _encode(digest))
        )

    def verify(self, password: str, stored: str) -> bool:
        """Проверяет пароль по его хранимой форме.

        Форма, которую этот хешер не умеет читать, отвергается, а не разбирается
        снисходительно: снисходительный разбор превращает испорченную строку в
        успешный вход.

        Args:
            password: Проверяемый пароль.
            stored: Хранимая форма, полученная :meth:`hash`.

        Returns:
            bool: True, когда пароль совпал.
        """
        algorithm, iterations, salt, expected = _split(stored)
        if not algorithm.startswith(f"{ALGORITHM_PREFIX}_"):
            return False
        digest_name = algorithm.removeprefix(f"{ALGORITHM_PREFIX}_")
        try:
            digest = hashlib.pbkdf2_hmac(
                digest_name, password.encode("utf-8"), salt, iterations, dklen=KEY_LENGTH_BYTES
            )
        except ValueError:
            return False
        return hmac.compare_digest(digest, expected)

    @property
    def _label(self) -> str:
        """Возвращает имя алгоритма, с которым записана строка."""
        return f"{ALGORITHM_PREFIX}_{self._digest}"


def _split(stored: str) -> tuple[str, int, bytes, bytes]:
    """Разбирает хранимую форму на имя алгоритма, стоимость, соль и дайджест."""
    parts = stored.split(FIELD_SEPARATOR)
    if len(parts) != 4:
        raise ValueError("stored password is not a self describing PBKDF2 form")
    algorithm, raw_iterations, raw_salt, raw_digest = parts
    return algorithm, int(raw_iterations), _decode(raw_salt), _decode(raw_digest)


def _encode(raw: bytes) -> str:
    """Кодирует байты без выравнивающих знаков равно."""
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    """Декодирует байты, возвращая отсутствующее выравнивание."""
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
