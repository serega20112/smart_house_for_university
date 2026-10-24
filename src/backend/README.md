# Пакет `backend`

Вся серверная логика умного дома. Описание продукта, запуск, настройка и проверки —
в [корневом README](../../README.md); устройство системы целиком —
в [docs/architecture/overview.md](../../docs/architecture/overview.md). Здесь остаётся
только то, что нельзя прочитать снаружи пакета: карта слоёв и правило, по которому они
смотрят друг на друга.

## Слои

```text
composition     точка входа процесса: читает конфигурацию, собирает граф роли,
                назначает жизненный цикл и запускает uvicorn или ARQ
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
Композиция — единственный слой, которому позволено знать всех: он решает, с какой
конфигурацией процесс живёт, собирает граф его роли, берёт жизненный цикл над этим
графом и запускает процесс. Обратного знания нет: ни один слой не импортирует
`backend.composition`.

## Плата

Плата дозванивается до бэкенда сама как WebSocket-клиент и объявляет ключ сопряжения.
Бэкенд разрешает этот ключ в аккаунт, и с этого момента кадры её сокета обновляют
состояние только этого аккаунта. Протокол кадров — в
[docs/hardware/esp-protocol.md](../../docs/hardware/esp-protocol.md).
