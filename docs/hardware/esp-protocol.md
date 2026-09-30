# Протокол Backend ↔ ESP8266 (v1)

## Транспорт

* WebSocket. ESP8266 — **клиент**, backend — **сервер** (`ws://<backend-host>:8765/esp`).
* Каждое сообщение — один JSON-объект в текстовом фрейме.
* Версия протокола передаётся ESP в первом сообщении `HELLO` сразу после
  установления соединения.

## Инициализация

После подключения ESP отправляет:

```json
{"type": "HELLO", "firmware_version": "1.0.0", "protocol_version": 1}
```

Backend отвечает полным запросом состояния:

```json
{"type": "GET_STATE"}
```

ESP немедленно отправляет `STATE` (см. ниже) — это закрывает требование
синхронизации после восстановления связи (ТЗ п.26).

## Backend → ESP

### SET_RELAY

```json
{"type": "SET_RELAY", "command_id": "c-16f", "channel": 3, "state": true}
```

| Поле | Тип | Описание |
| --- | --- | --- |
| `command_id` | string | Идентификатор команды, возвращается в ACK |
| `channel` | int 1..6 | Физический канал реле (нумерация фиксирована в прошивке) |
| `state` | bool | `true` — включить, `false` — выключить |

ESP обязан ответить `ACK` с тем же `command_id` и затем `STATE`
с обновлённым состоянием всех реле.

### GET_STATE

```json
{"type": "GET_STATE"}
```

ESP отвечает `STATE`.

## ESP → Backend

### STATE

```json
{
  "type": "STATE",
  "relays": [false, true, false, false, true, false],
  "temperature": 22.4,
  "humidity": 46.2
}
```

* `relays[0..5]` — состояния каналов 1..6 (`true` = включено).
* `temperature` / `humidity` могут отсутствовать, если датчик ещё не дал
  валидных показаний.

Отправляется: по `GET_STATE`, сразу после выполнения `SET_RELAY`,
и периодически (каждые ~5 с).

### SENSOR_DATA

```json
{"type": "SENSOR_DATA", "temperature": 22.4, "humidity": 46.2}
```

Периодические показания DHT22 (без состояния реле).

### ACK

```json
{"type": "ACK", "command_id": "c-16f"}
```

### ERROR

```json
{"type": "ERROR", "code": "BAD_CHANNEL", "message": "channel out of range 1..6"}
```

| Код | Значение |
| --- | --- |
| `BAD_MESSAGE` | сообщение без поля `type` |
| `BAD_COMMAND` | отсутствующие поля команды |
| `BAD_CHANNEL` | канал вне диапазона 1..6 |
| `UNKNOWN_TYPE` | неподдерживаемый `type` |
| `SENSOR_READ_FAILED` | DHT22 не отдаёт валидных показаний |

## Обработка потери связи

* Backend считает ESP недоступной, если соединение закрыто или нет сообщений
  дольше `ESP_WATCHDOG_SEC` (двойной период телеметрии). Все устройства
  переходят в `UNAVAILABLE` (ТЗ п.26).
* ESP при потере соединения автоматически переподключается (интервал 3 с)
  и после восстановления отправляет `HELLO` + `STATE`.
