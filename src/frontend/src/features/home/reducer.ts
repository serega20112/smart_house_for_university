/**
 * Превращение события realtime-канала в заплатку снимка дома.
 *
 * Плата приносит показания каждые несколько секунд, поэтому перезапрашивать весь
 * экран на каждое событие смысла нет: часть изменений дописывается в уже
 * прочитанный снимок. Всё, чего заплатка выразить не может — список устройств или
 * очередь сценариев, — честно требует чтения заново.
 */

import type { DeviceStatus, HomeState, RealtimeEvent } from "../../services/types";

export type StatePatch = Partial<HomeState>;

/** События, после которых снимок перечитывают целиком. */
const RELOAD_EVENTS: RealtimeEvent[] = [
  "devices.updated",
  "scenario.scheduled",
  "scenario.started",
  "scenario.finished",
  "automation.updated",
  "board.online",
  "board.offline",
  "board.paired",
  "board.network_changed",
  "board.announcement_published",
];

/**
 * Сообщает, можно ли изменить снимок на месте или нужно перечитать.
 *
 * @param type Имя пришедшего события.
 * @returns True, когда заплатка не выражает случившееся.
 */
export function needsReload(type: RealtimeEvent): boolean {
  return RELOAD_EVENTS.includes(type);
}

/**
 * Применяет одно событие к снимку дома без перезапроса.
 *
 * @param state Текущий снимок.
 * @param type Имя пришедшего события.
 * @param payload Данные, которые событие несёт.
 * @returns Поля для слияния; пусто, когда событие ничего не меняет локально.
 */
export function reduceEvent(
  state: HomeState,
  type: RealtimeEvent,
  payload: Record<string, unknown>,
): StatePatch {
  switch (type) {
    case "sensor.temperature_changed":
      return readingPatch(state, "temperature", payload);
    case "sensor.humidity_changed":
      return readingPatch(state, "humidity", payload);
    case "device.state_changed":
    case "board.relay_changed":
      return { devices: patchDeviceStatus(state.devices, payload) };
    default:
      return {};
  }
}

/**
 * Возвращает заплатку одного измеренного значения, не трогая второе.
 *
 * @param state Снимок, к которому применяют изменение.
 * @param key Какое значение климата пришло.
 * @param payload Данные события.
 * @returns Поля для слияния.
 */
function readingPatch(
  state: HomeState,
  key: "temperature" | "humidity",
  payload: Record<string, unknown>,
): StatePatch {
  const value = payload[key];
  if (typeof value !== "number") {
    return {};
  }
  return { reading: { ...state.reading, [key]: value } };
}

/**
 * Меняет состояние одного устройства, не трогая остальные.
 *
 * @param devices Устройства снимка.
 * @param payload Данные события: идентификатор и новое состояние.
 * @returns Новый список устройств.
 */
function patchDeviceStatus(devices: HomeState["devices"], payload: Record<string, unknown>) {
  const deviceId = payload.device_id;
  const status = payload.status;
  if (typeof deviceId !== "string" || typeof status !== "string") {
    return devices;
  }
  return devices.map((device) =>
    device.id === deviceId ? { ...device, status: status as DeviceStatus } : device,
  );
}
