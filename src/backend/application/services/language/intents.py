"""Чтение намерения из того, что выпустил конвейер понимания.

Конвейеры отдают намерение каждый по-своему: один — уже перечислением, другой —
строкой из ответа модели. Здесь значение приводится к одному виду, потому что
разбор сырого ответа — дело адаптера, а плоский перенос данных между слоями логики
не держит.
"""

from __future__ import annotations

from backend.application.dto.language.intent import Intent


def intent_of(raw: object) -> Intent | None:
    """Возвращает намерение по значению из ответа конвейера.

    Args:
        raw: То, что отдали распознаватель или модель: намерение, строка или None.

    Returns:
        Intent | None: Названное намерение либо None, когда названо что-то другое.
    """
    if isinstance(raw, Intent):
        return raw
    if raw is None:
        return None
    try:
        return Intent(str(raw).strip().upper())
    except ValueError:
        return None
