"""Превращает фразы в векторы.

Классификатор сравнивает смыслы, поэтому настоящий смысловой кодировщик ему нужен.
Хешированный мешок слов не отличит «выключи свет» от «включи свет» ни в каком важном
направлении, поэтому запасного кодировщика в этом пакете нет: система, молча скатывающаяся
к бессмысленному сходству, хуже системы, которая отказывается запускаться.

Модель берут из конфигурации, и отсутствующая зависимость поднимает
:class:`EmbeddingsUnavailableError` до того, как будет обслужен первый запрос.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

from backend.application.interfaces.services.language.embedder import Embedder
from backend.infrastructure.system.logging import get_logger

log = get_logger("nlp.embeddings")

INSTALL_HINT = (
    "sentence-transformers is required for the local intent classifier; "
    "install the optional extra with 'pip install .[embeddings]'"
)


class EmbeddingsUnavailableError(RuntimeError):
    """Модель кодирования предложений не удаётся загрузить.

    Args:
        model_name: Название запрошенной модели.
        reason: О чём сообщил загрузчик.
    """

    def __init__(self, model_name: str, reason: str) -> None:
        """Инициализирует отказ.

        Args:
            model_name: Название запрошенной модели.
            reason: О чём сообщил загрузчик.
        """
        super().__init__(f"cannot load the embedding model {model_name!r}: {reason}")
        self.model_name = model_name


class SentenceTransformerEmbedder(Embedder):
    """Кодировщик на многоязычной модели sentence transformers.

    Attributes:
        model_name: Название модели sentence transformers.
        device: Устройство torch, на котором идут выводы.
        dimensions: Ожидаемая длина полученного вектора.

    Raises:
        EmbeddingsUnavailableError: Когда библиотеку или модель не удалось загрузить.
    """

    def __init__(self, model_name: str, device: str, dimensions: int) -> None:
        """Загружает модель.

        Args:
            model_name: Название модели sentence transformers.
            device: Устройство torch, на котором идут выводы.
            dimensions: Ожидаемая длина полученного вектора.

        Raises:
            EmbeddingsUnavailableError: Когда библиотеку или модель не удалось
                загрузить.
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as error:
            raise EmbeddingsUnavailableError(model_name, INSTALL_HINT) from error
        try:
            self._model = SentenceTransformer(model_name, device=device)
        except Exception as error:
            raise EmbeddingsUnavailableError(model_name, str(error)) from error
        self._dimensions = dimensions
        self._name = model_name
        log.info(
            "nlp.embedder_loaded",
            model=model_name,
            device=device,
            dimensions=dimensions,
        )

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        """Возвращает векторное представление каждой фразы.

        Args:
            texts: Фразы для кодирования.

        Returns:
            list[list[float]]: По одному нормированному вектору на фразу.

        Raises:
            EmbeddingsUnavailableError: Когда модель дала вектор неожиданной длины —
                иначе каждая выдача молча портилась бы.
        """
        if not texts:
            return []
        vectors = self._model.encode(
            list(texts), normalize_embeddings=True, show_progress_bar=False
        )
        encoded = [[float(value) for value in vector] for vector in vectors]
        for vector in encoded:
            if len(vector) != self._dimensions:
                raise EmbeddingsUnavailableError(
                    self._name,
                    f"the model produced {len(vector)} dimensions instead of {self._dimensions}",
                )
        return encoded

    async def encode_async(self, texts: Sequence[str]) -> list[list[float]]:
        """Возвращает векторное представление фраз, не занимая цикл событий.

        Args:
            texts: Фразы для кодирования.

        Returns:
            list[list[float]]: По одному нормированному вектору на фразу.
        """
        return await asyncio.to_thread(self.encode, texts)


def load_embedder(model_name: str, device: str, dimensions: int) -> Embedder:
    """Загружает кодировщик, названный в конфигурации.

    Args:
        model_name: Название модели sentence transformers.
        device: Устройство torch, на котором идут выводы.
        dimensions: Ожидаемая длина полученного вектора.

    Returns:
        Embedder: Загруженный кодировщик.

    Raises:
        EmbeddingsUnavailableError: Когда библиотеку или модель не удалось загрузить.
    """
    return SentenceTransformerEmbedder(model_name, device, dimensions)
