# Архитектура системы

## Три уровня ответственности (ТЗ п.42)

```text
ESP8266        -> физическое исполнение (реле, датчик) и трансляция показаний
Backend        -> ВСЯ бизнес-логика: устройства, автоматизация, сценарии, NLP
Frontend / TG  -> только интерфейс пользователя
```

* ESP8266 не принимает решений за систему.
* Frontend и Telegram не управляют ESP напрямую.
* Backend — единственная точка, через которую проходят команды и автоматизация.
* Clean Architecture применяется **только к backend**.

## Общая схема

```text
                    ┌─────────────────┐
                    │    Frontend     │
                    └────────┬────────┘
                             │ REST + WebSocket
                             ▼
                    ┌─────────────────┐
                    │     Backend     │
                    │ Clean           │
                    │ Architecture    │
                    └────────┬────────┘
                             │
                 ┌───────────┴───────────┐
                 │                       │
                 ▼                       ▼
          ┌─────────────┐         ┌─────────────┐
          │  Telegram   │         │    ESP8266  │
          └─────────────┘         └──────┬──────┘
                                         │
                              ┌──────────┴──────────┐
                              │                     │
                           DHT22                Relay ×6
```

ESP8266 устанавливает **исходящее** WebSocket-соединение к backend
(`ws://<backend>:8765/esp`), поэтому ESP не обязан иметь стабличный IP и
не принимает входящих соединений. Backend держит сервер `websockets` на порту 8765.

## Слои backend

```text
Presentation  (FastAPI REST, WebSocket для frontend, Telegram-хендлеры)
     ↓
Application   (commands/queries — use cases, движки автоматизации и сценариев)
     ↓
Domain        (сущности, value objects, enums, интерфейсы репозиториев, доменные сервисы)
     ↑
Infrastructure (SQLAlchemy, ESP-клиент, Telegram API, embeddings/NLP)
```

Зависимости направлены внутрь. Domain не знает про FastAPI, SQLAlchemy,
Telegram, ESP и конкретную библиотеку embeddings — он зависит только от
абстрактных интерфейсов (`repositories/`, порты в application).

## Ключевые решения

| Решение | Обоснование |
| --- | --- |
| Логические устройства ≠ физические реле | Пользователь переименовывает/переназначает каналы без прошивки (ТЗ п.10) |
| capabilities (ON/OFF/COOL/HEAT) | Автоматизация ищет устройство по возможности, а не по имени (ТЗ п.11) |
| Единый `ProcessUserCommand` | Web, Telegram и будущий голосовой интерфейс сходятся в один pipeline (ТЗ п.12, 38) |
| Hysteresis-диапазон | Защита от дребезга включения около цели (ТЗ п.21) |
| Приоритеты: аварийные > сценарий > автоматика > ручное | Детерминированное поведение при конфликтах (ТЗ п.25) |
| MANUAL_OVERRIDE с таймером | Ручная команда временно глушит автоматику |
| Embeddings + fallback-скорер | Понимание формулировок без LLM; при недоступности модели — лексический fallback (ТЗ п.15–17) |

## NLP-pipeline (ТЗ п.15)

```text
Нормализация → Embedding → Векторный поиск → Intent → Парсер параметров
→ StructuredCommand → Application
```

При уверенности ниже `NLP_CONFIDENCE_THRESHOLD` команда не выполняется —
система просит уточнение (ТЗ п.17, критерий 15).

## Потоки событий

1. ESP присылает `STATE`/`SENSOR_DATA` → `EspClient` обновляет `HomeState` →
   `EventBus` рассылает события → WebSocket frontend + Telegram-уведомления.
2. Команда пользователя → Application → Domain-проверка capabilities →
   `EspClient.set_relay()` → ожидание `ACK` → событие `device.state_changed`.
3. `AutomationEngine` (цикл каждые `AUTOMATION_INTERVAL_SEC`) и
   `ScenarioEngine` (каждый `SCENARIO_TICK_SEC`) работают поверх того же
   executor'а, что и ручные команды.

Подробнее: [esp-protocol.md](hardware/esp-protocol.md), [api.md](api/api.md).
