"""Хеширование паролей.

Хранимая форма описывает себя сама: называет алгоритм, число повторов и соль, из
которой она получилась, поэтому стоимость можно поднять позже без переноса уже
записанных строк. Проверка сравнивает дайджесты за постоянное время.

bcrypt не выбран осознанно: он требует отдельной зависимости и обрезает пароль на
72 байтах, а PBKDF2-HMAC лежит в стандартной библиотеке. Хранимая форма начинается
с имени алгоритма, поэтому переход на bcrypt или argon2 остаётся шагом кода, а не
переносом данных: строки, записанные прежней веткой, продолжит проверять прежний
код.

Вывод ключа считается в отдельном потоке. Сотни миллисекунд PBKDF2 на цикле
событий — это остановленные кадры плат и сокеты интерфейса всех остальных домов,
поэтому ни одна сверка не выполняется там, где крутится цикл.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import hmac
import secrets

from backend.application.interfaces.services.security.password_hasher import PasswordHasher

ALGORITHM_PREFIX = "pbkdf2"
DEFAULT_DIGEST = "sha256"
KEY_LENGTH_BYTES = 32
FIELD_SEPARATOR = "$"
ITERATION_HEADROOM = 5
MISS_DIGEST = b"\x00" * KEY_LENGTH_BYTES


class Pbkdf2PasswordHasher(PasswordHasher):
    """Выводит хранимые пароли через PBKDF2-HMAC.

    Attributes:
        iterations: Число витков одного вывода; стоит дороже линейно и касается
            только что записанных паролей.
        salt_bytes: Длина соли одного пароля.
        digest: Хеш, используемый внутри PBKDF2.
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
        """
        self._iterations = iterations
        self._salt_bytes = salt_bytes
        self._digest = digest
        self._miss_salt = secrets.token_bytes(salt_bytes)

    async def hash(self, password: str) -> str:
        """Производит хранимую форму пароля.

        Args:
            password: Пароль, который выбрал человек.

        Returns:
            str: Описывающая себя форма с солью и стоимостью.
        """
        return await asyncio.to_thread(self._derive, password)

    async def verify(self, password: str, stored: str | None) -> bool:
        """Проверяет пароль по его хранимой форме.

        Форма, которую этот хешер не умеет читать, отвергается, а не разбирается
        снисходительно: снисходительный разбор превращает испорченную строку в
        успешный вход. Отсутствие формы — тоже отказ, но за ту же стоимость, чтобы
        время ответа не говорило, существует ли аккаунт.

        Args:
            password: Проверяемый пароль.
            stored: Хранимая форма, полученная :meth:`hash`, или None, когда
                записи об аккаунте нет.

        Returns:
            bool: True, когда пароль совпал.
        """
        return await asyncio.to_thread(self._matches, password, stored)

    def _derive(self, password: str) -> str:
        """Считает хранимую форму с текущей стоимостью.

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

    def _matches(self, password: str, stored: str | None) -> bool:
        """Сверяет пароль с формой, считая ключ в текущем потоке.

        Args:
            password: Проверяемый пароль.
            stored: Хранимая форма или None, когда записи об аккаунте нет.

        Returns:
            bool: True, когда пароль совпал.
        """
        parts = _split(self._miss_form if stored is None else stored)
        if parts is None:
            return False
        algorithm, iterations, salt, expected = parts
        if not algorithm.startswith(f"{ALGORITHM_PREFIX}_"):
            return False
        if not 0 < iterations <= self._iterations * ITERATION_HEADROOM:
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

    @property
    def _miss_form(self) -> str:
        """Возвращает форму, по которой не проходит ни один пароль.

        Стоимость у неё текущая, а дайджест не является свёрткой никакого пароля,
        поэтому сверка стоит ровно столько же, сколько настоящая, и всегда
        отказывает.
        """
        return FIELD_SEPARATOR.join(
            (self._label, str(self._iterations), _encode(self._miss_salt), _encode(MISS_DIGEST))
        )


def _split(stored: str) -> tuple[str, int, bytes, bytes] | None:
    """Разбирает хранимую форму на имя алгоритма, стоимость, соль и дайджест.

    Args:
        stored: Хранимая форма, предложенная к разбору.

    Returns:
        tuple[str, int, bytes, bytes] | None: Части формы или None, когда строка не
        является формой пароля.
    """
    parts = stored.split(FIELD_SEPARATOR)
    if len(parts) != 4:
        return None
    algorithm, raw_iterations, raw_salt, raw_digest = parts
    try:
        return algorithm, int(raw_iterations), _decode(raw_salt), _decode(raw_digest)
    except (ValueError, binascii.Error):
        return None


def _encode(raw: bytes) -> str:
    """Кодирует байты без выравнивающих знаков равно."""
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    """Декодирует байты, возвращая отсутствующее выравнивание."""
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
