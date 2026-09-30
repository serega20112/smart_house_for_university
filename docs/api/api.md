# REST API backend

Base URL: `http://<host>:8000`. Все ответы — JSON. Realtime-события —
WebSocket `ws://<host>:8000/ws` (см. ниже).

## Состояние системы

| Метод | Путь | Описание |
| --- | --- | --- |
| GET | `/api/health` | `{backend: "online", esp: "online"/"offline"}` (ТЗ п.28) |
| GET | `/api/state` | Полный снимок: ESP-доступность, климат, устройства, автоматизация, активные сценарии, MANUAL_OVERRIDE |

## Устройства (ТЗ п.29)

| Метод | Путь | Описание |
| --- | --- | --- |
| GET | `/api/devices` | Список устройств |
| POST | `/api/devices` | Создать устройство `{name, type, physical_channel, capabilities[], enabled, automation_enabled}` |
| PATCH | `/api/devices/{id}` | Изменить название/тип/канал/участие в автоматизации |
| DELETE | `/api/devices/{id}` | Удалить устройство |
| POST | `/api/devices/{id}/on` | Включить (capability ON) |
| POST | `/api/devices/{id}/off` | Выключить |
| POST | `/api/devices/{id}/mode` | `{mode: "COOL" | "HEAT" | "OFF"}` |

Ошибки: `409` — устройство не поддерживает действие (нет capability),
`503` — ESP недоступен (ТЗ п.26), `404` — нет устройства.

## Автоматизация (ТЗ п.30)

| Метод | Путь | Описание |
| --- | --- | --- |
| GET | `/api/automation` | Настройки: `enabled, target_temperature, min/max_temperature, target_humidity, min/max_humidity` |
| PUT | `/api/automation` | Обновить настройки (частично) |
| POST | `/api/automation/enable` | Включить режим AUTO |
| POST | `/api/automation/disable` | Выключить режим AUTO |

## Сценарии (ТЗ п.23–24)

| Метод | Путь | Описание |
| --- | --- | --- |
| GET | `/api/scenarios` | Все сценарии (с фильтрами `?status=pending`) |
| POST | `/api/scenarios` | Создать `{start_at | delay_minutes, target, actions[], completion_behavior}` |
| DELETE | `/api/scenarios/{id}` | Отменить (CANCELLED) |

`completion_behavior`: `OFF | RESTORE_PREVIOUS_STATE | CONTINUE_AUTOMATION`.

## Команды (ТЗ п.14.1, 15–19)

| Метод | Путь | Описание |
| --- | --- | --- |
| POST | `/api/commands` | `{text: "включи свет"}` — единый NLP-pipeline для Web/Telegram/голоса |

Ответ:

```json
{
  "ok": true,
  "intent": "TURN_ON",
  "confidence": 0.91,
  "message": "Включаю Основной свет.",
  "requires_clarification": false
}
```

При уверенности ниже порога: `requires_clarification: true` и просьба уточнить.

## WebSocket frontend

`GET /ws` — сервер отправляет JSON-события (ТЗ п.33):

```json
{"type": "device.state_changed", "payload": {"device_id": 1, "state": "ON"}}
```

Типы: `device.state_changed`, `sensor.temperature_changed`,
`sensor.humidity_changed`, `esp.connected`, `esp.disconnected`,
`automation.state_changed`, `scenario.created`, `scenario.started`,
`scenario.completed`, `scenario.failed`, `devices.updated`, `command.reply`.

## Telegram

Бот (`presentation/telegram`) принимает текстовые сообщения, прогоняет их
через `POST`-эквивалент `/api/commands` (тот же `ProcessUserCommand`) и
отвечает текстом. Значимые события дублируются в `TELEGRAM_CHAT_ID`
(ТЗ п.32).
