# Бэкенд умного дома

Многопользовательская платформа: один процесс обслуживает любое число аккаунтов, и
каждый получает своё — свои устройства, настройки, автоматизации, сценарии и свой
главный экран. Владелец берётся из сессии, а не из тела запроса, поэтому подстановка
чужого идентификатора не даёт ничего.

## Слои

```text
presentation    api/v1 (тонкие маршруты) + requests/responses, websockets (эндпоинт),
                telegram (разговор), web; ошибки, фразы и сборка приложения — модулями
                в корне слоя
application     use_cases (по одному сценарию в файле), services, dto (плоские),
                interfaces (порты по подпакетам), errors
domain          aggregates (только корни), entities (дочерние сущности), value_objects
                (значения, enum'ы, модели чтения), policies, exceptions, identifiers,
                events
infrastructure  database (engine, unit_of_work, models, mappers, repositories, queries),
                brokers, esp, nlp, security, telegram, websockets, workers, system
                (часы и журнал), di (providers/app и providers/use_cases)
```

Зависимости направлены внутрь: домен не знает ни фреймворков, ни слоёв выше него, а
прикладной слой не заглядывает в инфраструктуру. Границы проверяет `import-linter`.
Жизнью подсистем процесса (транспорт плат, концентратор событий, бот, посев индекса)
ведёт `backend/events/lifecycle.py` — композиционный корень, а не презентация.

## Запуск

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env                  # и задать AUTH_TOKEN_SECRET
PYTHONPATH=src python -m backend.main
```

Интерфейс — на <http://127.0.0.1:8000>, описание API — на `/docs`. Второй процесс,
фоновые циклы, запускают отдельно:

```bash
PYTHONPATH=src python -m backend.worker_entry
```

Схема базы ведётся ревизиями из `build/migrations`:

```bash
PYTHONPATH=src .venv/bin/alembic -c build/migrations/alembic.ini upgrade head
```

`AUTH_TOKEN_SECRET` задают обязательно: без него процесс не стартует. Остальные
параметры читаются из окружения, у каждой секции свой файл в `config/sections`, а
плоский `Settings` собирает их вместе.

## Плата

Плата дозванивается до бэкенда сама как WebSocket-клиент и объявляет ключ сопряжения.
Бэкенд разрешает этот ключ в аккаунт, и с этого момента кадры её сокета обновляют
состояние только этого аккаунта. Протокол кадров — в `docs/hardware/esp-protocol.md`.

## Проверки

```bash
ruff check src tests scripts
ruff format src tests scripts
lint-imports
PYTHONPATH=src python scripts/check_app_wires.py
pytest
```

`check_app_wires.py` разрешает каждый узел графа зависимостей и печатает опубликованные
маршруты: контейнер ленивый, и провайдер с неподходящей сигнатурой всплывает только
когда ключ впервые попросили.
