"""Сперва спрашивает удалённую модель, потом переходит на местный конвейер.

Когда развёртывание держит собственную службу моделей, та уже содержит модели, нужные
предложению. Поэтому связка с ней — вопрос композции, а не правило какого-либо сервиса:
:class:`RemoteFirstUnderstanding` оборачивает удалённый клиент и местный интерфейс и
сначала спрашивает удалённый.

Обрабатываются ровно два исхода, которые удалённая модель вправе выдать: ответ или
заявление, что она недоступна. Всё остальное — ошибка, и она продолжается как ошибка
вместо молчаливого понижения.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from backend.application.dto.language.command_understanding import CommandUnderstanding
from backend.application.dto.language.intent import Intent
from backend.application.interface.services.command_understanding_port import (
    CommandUnderstandingPort,
)
from backend.domain.value_objects.climate.temperature import Temperature
from backend.domain.value_objects.devices.capability import Capability
from backend.domain.value_objects.devices.device_kind import DeviceKind
from backend.infrastructure.logging import get_logger

log = get_logger("nlp.remote")

UNDERSTAND_PATH = "/understand"


class RemoteUnderstandingUnavailable(RuntimeError):
    """Удалённая модель не смогла ответить.

    Args:
        reason: Машинночитаемая причина.
    """

    def __init__(self, reason: str) -> None:
        """Инициализирует отказ.

        Args:
            reason: Машинночитаемая причина.
        """
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class RemoteAnswer:
    """Одна структурированная команда в том виде, её передала удалённая модель.

    Attributes:
        intent: Название намерения или None, когда предложение не команда.
        confidence: Насколько уверена удалённая модель.
        device_name: Кусок имени устройства, найденный в предложении.
        device_kinds: Назначения устройств, о которых могло идти речь.
        capability: Способность, о которой просит предложение.
        temperature: Запрошенная температура, или None.
        humidity: Запрошенная влажность, или None.
        delay_minutes: Запрошенная задержка, или None.
        target: Запрошенное место, или None.
    """

    intent: str | None
    confidence: float
    device_name: str | None = None
    device_kinds: tuple[str, ...] = ()
    capability: str | None = None
    temperature: float | None = None
    humidity: float | None = None
    delay_minutes: int | None = None
    target: str | None = None


class RemoteUnderstandingClient:
    """Спрашивает у машины, крутящей модели, что значит предложение.

    Attributes:
        client: Соединение с хостом моделей.
        base_url: Адрес хоста моделей.
        timeout_sec: Таймаут одного запроса в секундах.
    """

    def __init__(self, client: httpx.AsyncClient, base_url: str, timeout_sec: float) -> None:
        """Инициализирует клиент.

        Args:
            client: Соединение с хостом моделей.
            base_url: Адрес хоста моделей.
            timeout_sec: Таймаут одного запроса в секундах.
        """
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
        return _answer_of(payload)


class RemoteFirstUnderstanding(CommandUnderstandingPort):
    """Сначала спрашивает удалённую модель, потом местный конвейер.

    Attributes:
        remote: Клиент машины, крутящей модели, или None, когда развёртывание её
            не имеет.
        local: Конвейер, используемый всякий раз, когда у удалённой модели ответа нет.
    """

    def __init__(
        self, remote: RemoteUnderstandingClient | None, local: CommandUnderstandingPort
    ) -> None:
        """Инициализирует составной интерфейс.

        Args:
            remote: Клиент машины, крутящей модели, или None, когда развёртывание её
                не имеет.
            local: Конвейер, используемый всякий раз, когда у удалённой модели ответа нет.
        """
        self._remote = remote
        self._local = local

    async def understand(self, text: str) -> CommandUnderstanding:
        """Толкует предложение.

        Args:
            text: Предложение в сыром виде, каким его получил интерфейс.

        Returns:
            CommandUnderstanding: То, что из него сделал конвейер.
        """
        answer = await self._remote_answer(text)
        if answer is None:
            return await self._local.understand(text)
        return understanding_of(answer)

    async def is_confident_enough(self, understanding: CommandUnderstanding) -> bool:
        """Сообщает, можно ли выполненное понимание пускать в дело.

        Args:
            understanding: Результат конвейера.

        Returns:
            bool: True, когда команде можно идти дальше.
        """
        return await self._local.is_confident_enough(understanding)

    async def _remote_answer(self, text: str) -> RemoteAnswer | None:
        if self._remote is None:
            return None
        try:
            return await self._remote.ask(text)
        except RemoteUnderstandingUnavailable as unavailable:
            log.info("nlp.remote_unavailable", reason=unavailable.reason)
            return None


def _answer_of(payload: dict[str, object]) -> RemoteAnswer:
    kinds = payload.get("device_kinds")
    return RemoteAnswer(
        intent=None if payload.get("intent") is None else str(payload["intent"]),
        confidence=_as_score(payload.get("confidence")),
        device_name=_as_text(payload.get("device_name")),
        device_kinds=tuple(str(item) for item in kinds) if isinstance(kinds, list) else (),
        capability=_as_text(payload.get("capability")),
        temperature=_as_float(payload.get("temperature"), None),
        humidity=_as_float(payload.get("humidity"), None),
        delay_minutes=_as_int(payload.get("delay_minutes"), None),
        target=_as_text(payload.get("target")),
    )


def understanding_of(answer: RemoteAnswer) -> CommandUnderstanding:
    temperature = answer.temperature
    return CommandUnderstanding(
        intent=Intent.parse(answer.intent),
        device_name=answer.device_name,
        device_kinds=frozenset(_kinds_of(answer.device_kinds)),
        capability=_capability_of(answer.capability),
        temperature=None if temperature is None else Temperature(temperature),
        humidity=answer.humidity,
        delay_minutes=answer.delay_minutes,
        target=answer.target,
        confidence=answer.confidence,
    )


def _kinds_of(names: tuple[str, ...]) -> frozenset[DeviceKind]:
    found: set[DeviceKind] = set()
    for name in names:
        try:
            found.add(DeviceKind.parse(name))
        except ValueError:
            continue
    return frozenset(found)


def _capability_of(name: str | None) -> Capability | None:
    if name is None:
        return None
    try:
        return Capability.parse(name)
    except ValueError:
        return None


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
