"""Конвейер понимания свободных формулировок."""

from __future__ import annotations

import os

from backend.config.sections.parsing import as_bool


def language_model_name() -> str:
    """Название модели, кодирующей предложение."""
    return os.getenv("LANGUAGE_MODEL_NAME", "paraphrase-multilingual-MiniLM-L12-v2")


def language_embedding_dimensions() -> int:
    """Длина вектора, который производит модель.

    Returns:
        int: Размерность.
    """
    return int(os.getenv("LANGUAGE_EMBEDDING_DIMENSIONS", "384"))


def language_device() -> str:
    """Устройство, на котором считается модель.

    Returns:
        str: Имя устройства.
    """
    return os.getenv("LANGUAGE_DEVICE", "cpu")


def language_confidence_threshold() -> float:
    """Насколько уверенным должен быть конвейер, чтобы действовать.

    Returns:
        float: Порог уверенности от нуля до единицы.
    """
    return float(os.getenv("LANGUAGE_CONFIDENCE_THRESHOLD", "0.55"))


def language_neural_commands() -> bool:
    """Спрашивается ли сначала удалённое понимание.

    Returns:
        bool: True, когда нейронные команды включены.
    """
    return as_bool(os.getenv("LANGUAGE_NEURAL_COMMANDS", "1"))


def language_bootstrap_url() -> str:
    """Адрес удалённого сервиса понимания.

    Returns:
        str: Базовый адрес или пустая строка, если сервиса нет.
    """
    return os.getenv("LANGUAGE_BOOTSTRAP_URL", "")


def language_timeout_sec() -> float:
    """Сколько может длиться вызов к сервису понимания.

    Returns:
        float: Секунды ожидания ответа.
    """
    return float(os.getenv("LANGUAGE_TIMEOUT_SEC", "30.0"))
