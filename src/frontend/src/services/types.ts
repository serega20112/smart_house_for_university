/**
 * Формы, которые отдаёт REST API бэкенда.
 *
 * Здесь повторяется только то, что уже записано в ответах прикладного слоя:
 * идентификаторы агрегатов — строки, климат приходит в единицах измерения, а
 * перечисления совпадают с доменными по names. Расхождение в одном имени ломает
 * экран, поэтому имена сверяются с `presentation/api/responses`, а не выдумываются.
 */

/** Способность, которую устройство умеет выполнить. */
export type Capability = "ON" | "OFF" | "COOL" | "HEAT" | "HUMIDIFY" | "DEHUMIDIFY";

/** Логическое состояние устройства: что оно делает сейчас. */
export type DeviceStatus =
  | "OFF"
  | "ACTIVE"
  | "COOLING"
  | "HEATING"
  | "HUMIDIFYING"
  | "DEHUMIDIFYING"
  | "UNAVAILABLE";

/** Назначение устройства. */
export type DeviceKind =
  | "LIGHT"
  | "FAN"
  | "HUMIDIFIER"
  | "DEHUMIDIFIER"
  | "AIR_CONDITIONER"
  | "HEATER"
  | "OUTLET"
  | "OTHER";

/** Готовый компонент, который интерфейс умеет нарисовать сам. */
export type WidgetType = "climate" | "sensor" | "device" | "command";

/** Что делать с устройствами после того, как сценарий закончится. */
export type CompletionBehavior =
  | "LEAVE_TO_AUTOMATION"
  | "SWITCH_EVERYTHING_OFF"
  | "RESTORE_CAPTURED_STATE";

/** Имена событий realtime-канала; один в один с `domain/events.py`. */
export type RealtimeEvent =
  | "board.online"
  | "board.offline"
  | "board.error"
  | "board.paired"
  | "board.network_changed"
  | "board.relay_changed"
  | "board.announcement_published"
  | "devices.updated"
  | "device.state_changed"
  | "automation.updated"
  | "scenario.scheduled"
  | "scenario.started"
  | "scenario.finished"
  | "sensor.temperature_changed"
  | "sensor.humidity_changed";

/** Аккаунт таким, каким его показывает интерфейс. */
export interface UserProfile {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
}

/** Сессия, выданная клиенту. */
export interface Session {
  access_token: string;
  token_type: string;
  expires_at: string;
  user: UserProfile;
}

/** Настройки собственной проекции дома. */
export interface Preferences {
  temperature_unit: "C" | "F";
  theme: "dark" | "light";
  language: "ru" | "en";
  show_command_chat: boolean;
}

/** Одна карточка главного экрана. */
export interface Widget {
  type: WidgetType;
  device_id: string | null;
  title: string | null;
}

/** Раскладка главного экрана одного аккаунта. */
export interface Dashboard {
  widgets: Widget[];
}

/** Плата такой, какой её видит интерфейс. */
export interface Board {
  id: string;
  name: string;
  online: boolean;
  last_seen_at: string | null;
  current_ssid: string | null;
}

/** Плата, только что сопряжённая: ключ показан ровно один раз. */
export interface PairedBoard {
  id: string;
  name: string;
  pairing_key: string;
}

/** Предложение платы, которая ждёт хозяина. */
export interface BoardClaim {
  id: string;
  label: string;
  claim_token: string;
  announced_at: string;
  expires_at: string;
}

/** Сеть, которую предписано использовать плате. */
export interface BoardNetwork {
  board_id: string;
  ssid: string;
  host: string;
  server_port: number;
  socket_port: number;
  socket_path: string;
  configured: boolean;
  updated_at: string | null;
}

/** Логическое устройство поверх релейного канала. */
export interface Device {
  id: string;
  name: string;
  kind: DeviceKind;
  channel: number;
  capabilities: Capability[];
  enabled: boolean;
  automation_enabled: boolean;
  status: DeviceStatus;
}

/** Настройка автоматизации: цели, допуски и участники. */
export interface Automation {
  enabled: boolean;
  target_temperature: number;
  target_humidity: number;
  temperature_tolerance: number;
  humidity_tolerance: number;
  participating_device_ids: string[];
}

/** Одно действие сценария. */
export interface ScenarioAction {
  capability: Capability;
  target_temperature: number | null;
}

/** Отложенное действие, обещанное собственному дому. */
export interface Scenario {
  id: string;
  status: string;
  created_at: string;
  start_at: string;
  duration_minutes: number | null;
  target: string | null;
  completion_behavior: CompletionBehavior;
  actions: ScenarioAction[];
}

/** Измеренные значения климата. */
export interface Reading {
  temperature: number | null;
  humidity: number | null;
}

/** Весь главный экран одним снимком. */
export interface HomeState {
  board_online: boolean;
  automation_suspended: boolean;
  reading: Reading;
  devices: Device[];
  automation: Automation;
  active_scenarios: Scenario[];
}

/** Ответ на высказанную свободную команду. */
export interface CommandResult {
  intent: string | null;
  answer: string;
  message: string;
  details: Record<string, unknown>;
}

/** Исход операции, которая изменила один признак или ничего. */
export interface OperationResult {
  status: string;
  message: string;
}
