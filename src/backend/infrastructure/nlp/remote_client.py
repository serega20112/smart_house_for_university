"""HTTP-клиент машины, крутящей модели понимания фраз.

Здесь только запрос и разбор ответа её протокола. Что делать с ответом и с чем его
сравнить, решает прикладной слой: недоступная модель не выключает дом, а составной
конвейер выбирает местный путь.
"""

from __future__ import annotations

import httpx

from backend.application.dto.language.remote_answer import RemoteAnswer
from backend.application.errors import RemoteUnderstandingUnavailable
from backend.application.interfaces.services.language.remote_understanding import (
    RemoteUnderstanding,
)
from backend.infrastructure.system.logging import get_logger

log = get_logger("nlp.remote")

UNDERSTAND_PATH = "/understand"


class RemoteUnderstandingClient(RemoteUnderstanding):
    """Спрашивает у службы моделей, что значит предложение.

    Attributes:
        client: Соединение с хостом моделей.
        base_url: Адрес хоста моделей.
        timeout_sec: Таймаут одного запроса в секундах.
    """

    def __init__(self, client: httpx.AsyncClient, base_url: str, timeout_sec: float) -> None:
        """Инициализирует клиент."""
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_sec

    async def ask(self, text: str) -> RemoteAnswer | None:
        """Просит удалённую модель понять предложение.

        Args:
            text: Предложение таким, каким его получил интерфейс.

        Returns:
            RemoteAnswer | None: Структурированная команда, или None, когда
            предложение вообще ни о какой команде не говорит.

        Raises:
            RemoteUnderstandingUnavailable: Когда удалённая модель не может ответить.
        """
        try:
            response = await self._client.post(
                f"{self._base_url}{UNDERSTAND_PATH}", json={"text": text}, timeout=self._timeout
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise RemoteUnderstandingUnavailable(type(error).__name__) from error
        if not isinstance(payload, dict):
            raise RemoteUnderstandingUnavailable("answer_is_not_an_object")
        return answer_of(payload)


def answer_of(payload: dict[str, object]) -> RemoteAnswer:
    """Превращает тело ответа модели в её структурированную команду."""
    kinds = payload.get("device_kinds")
    return RemoteAnswer(
        intent_name=None if payload.get("intent") is None else str(payload["intent"]),
        confidence=_as_score(payload.get("confidence")),
        device_name=_as_text(payload.get("device_name")),
        device_kinds=tuple(str(item) for item in kinds) if isinstance(kinds, list) else (),
        capability=_as_text(payload.get("capability")),
        temperature=_as_float(payload.get("temperature"), None),
        humidity=_as_float(payload.get("humidity"), None),
        delay_minutes=_as_int(payload.get("delay_minutes"), None),
        target=_as_text(payload.get("target")),
    )


def _as_text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _as_float(value: object, default: float | None) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return default
    return float(value)


def _as_score(value: object) -> float:
    """Возвращает уверенность ответа модели; отсутствующая считается нулём."""
    score = _as_float(value, None)
    return 0.0 if score is None else score


def _as_int(value: object, default: int | None) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return default
    return int(value)
