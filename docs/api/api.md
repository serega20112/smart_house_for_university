# REST API backend

Base URL: `http://<host>:8000`. Все ответы — JSON. Realtime-события —
WebSocket `ws://<host>:8000/ws` (см. ниже).

## Авторизация

Единственный способ узнать, кто делает запрос, — сессионный токен. Он
подставляется в заголовок `Authorization: Bearer <token>`. Идентификатор
пользователя, присланный клиентом в теле или в query, не читается никогда:
backend определяет аккаунт только из токена.

Публичных endpoint ровно три: регистрация, вход и проверка доступности backend.
Все остальные возвращают `401`, если токена нет или он невалиден.

| Метод | Путь | Описание |
| --- | --- | --- |
| POST | `/api/auth/register` | `{email, password, display_name}` → `201` с аккаунтом и токеном |
| POST | `/api/auth/login` | `{email, password}` → аккаунт и токен |
| POST | `/api/auth/logout` | Завершить сессию на клиенте |
| GET | `/api/auth/me` | Профиль текущего пользователя |
| GET | `/api/health` | `{backend: "online"}`, доступен без токена |

Ошибки: `409` — email уже занят, `422` — некорректный email, имя или слишком
короткий пароль (минимум 8 символов), `401` — неверные credentials.

## Состояние системы

| Метод | Путь | Описание |
| --- | --- | --- |
| GET | `/api/state` | Полный снимок текущего пользователя: доступность платы, климат, устройства, автоматизация, активные сценарии |
| GET | `/api/preferences` | Настройки интерфейса текущего пользователя |
| PATCH | `/api/preferences` | `{temperature_unit, theme, language, show_command_chat}` |
| GET | `/api/dashboard` | Состав главного экрана: упорядоченный список виджетов |
| PATCH | `/api/dashboard` | `{widgets: [{type, device_id, title}]}` |

Виджет `type` — одно из `climate`, `sensor`, `device`, `command`. Frontend не
знает этих имён заранее: он выбирает компонент по типу и передаёт ему
persoнальный `title`. Виджет со ссылкой на чужое устройство отклоняется с
`422`.

## Устройства

| Метод | Путь | Описание |
| --- | --- | --- |
| GET | `/api/devices` | Список устройств текущего пользователя |
| POST | `/api/devices` | Создать устройство `{name, type, physical_channel, capabilities[], enabled, automation_enabled}` |
| PATCH | `/api/devices/{id}` | Изменить название/тип/канал/участие в автоматизации |
| DELETE | `/api/devices/{id}` | Удалить устройство |
| POST | `/api/devices/{id}/on` | Включить (capability ON) |
| POST | `/api/devices/{id}/off` | Выключить |
| POST | `/api/devices/{id}/mode` | `{mode: "COOL" | "HEAT" | "OFF"}` |

Ошибки: `409` — устройство не поддерживает действие (нет capability) или канал
уже занят **внутри этого же аккаунта**, `503` — плата недоступна, `404` — нет
устройства.

Устройство чужого аккаунта читается как отсутствующее: подстановка чужого `id`
даёт `404`, а не его данные. Канал реле уникален внутри аккаунта, поэтому два
пользователя спокойно занимают один и тот же канал на своих платах.

## Платы (ESP)

| Метод | Путь | Описание |
| --- | --- | --- |
| GET | `/api/esp-devices` | Платы текущего пользователя с признаком `online` |
| POST | `/api/esp-devices` | Сопрячь плату `{name, pairing_key?}`. Ключ возвращается один раз |
| DELETE | `/api/esp-devices/{id}` | Отвязать плату |
| GET | `/api/esp-devices/{id}/network` | Настройки сети платы |
| PUT | `/api/esp-devices/{id}/network` | Задать сеть `{ssid, password, host, server_port, socket_port, socket_path}` |

Настройки сети меняются на лету: backend отправляет плате `SET_NETWORK`, плата
записывает их в свою память и переподключается. Настройки сохраняются и тогда,
когда плата сейчас не на связи: она получит их при следующем подключении.

Пароль сети в ответе не приходит никогда.

## Автоматизация

| Метод | Путь | Описание |
| --- | --- | --- |
| GET | `/api/automation` | Настройки: `enabled, target_temperature, min/max_temperature, target_humidity, min/max_humidity` |
| PUT | `/api/automation` | Обновить настройки (частично) |
| POST | `/api/automation/enable` | Включить режим AUTO |
| POST | `/api/automation/disable` | Выключить режим AUTO |
| POST | `/api/automation/run` | Прогнать один цикл вручную |

## Сценарии

| Метод | Путь | Описание |
| --- | --- | --- |
| GET | `/api/scenarios` | Активные сценарии текущего пользователя |
| POST | `/api/scenarios` | `{delay_minutes, target_temperature, capability, completion_behavior, target}` |
| DELETE | `/api/scenarios/{id}` | Отменить сценарий |

## Команды

| Метод | Путь | Описание |
| --- | --- | --- |
| POST | `/api/commands` | `{text}` — свободная формулировка на русском |

Команда исполняется в рамках аккаунта сессии: она видит только его устройства и
меняет только их состояние.

## Realtime

WebSocket `ws://<host>:8000/ws?token=<access_token>`. Браузер не умеет
прикреплять заголовок к WebSocket, поэтому токен передаётся параметром запроса и
проверяется тем же сервисом, что и REST.

Подписка привязана к аккаунту: соединение получает только события своего
пользователя. Типы событий: `device.state_changed`,
`sensor.temperature_changed`, `sensor.humidity_changed`, `esp.connected`,
`esp.disconnected`, `esp.error`, `automation.state_changed`,
`scenario.created`, `scenario.started`, `scenario.completed`,
`scenario.failed`, `devices.updated`.
