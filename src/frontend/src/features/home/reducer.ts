/** Reducers turning a realtime event into a state patch. */

import type { Device, HomeState, RealtimeEvent } from "../../services/types";

export type StatePatch = Partial<HomeState>;

/**
 * Tells whether an event changes something the incremental patch cannot
 * express, such as the list of devices or the active scenarios.
 */
export function needsReload(type: RealtimeEvent): boolean {
  return (
    type === "scenario.created" ||
    type === "scenario.started" ||
    type === "scenario.completed" ||
    type === "scenario.failed" ||
    type === "devices.updated" ||
    type === "esp.error"
  );
}

/**
 * Applies a single event to the home snapshot without refetching.
 *
 * The board reports sensor values every few seconds, so a full reload per event
 * would be both slow and wasteful.
 *
 * Args:
 * state: Current snapshot.
 * type: Name of the received event.
 * payload: Data carried by the event.

 * Returns:
 * StatePatch: Fields to merge, empty when the event changes nothing locally.
 */
export function reduceEvent(
  state: HomeState,
  type: RealtimeEvent,
  payload: Record<string, unknown>,
): StatePatch {
  switch (type) {
    case "sensor.temperature_changed":
      return numberPatch("temperature", payload);
    case "sensor.humidity_changed":
      return numberPatch("humidity", payload);
    case "esp.connected":
      return typeof payload.online === "boolean" ? { esp_online: payload.online } : {};
    case "esp.disconnected":
      return { esp_online: false };
    case "device.state_changed":
      return { devices: patchDeviceStatus(state.devices, payload) };
    case "automation.state_changed":
      return { automation: patchAutomation(state, payload) };
    default:
      return {};
  }
}

function numberPatch(
  key: "temperature" | "humidity",
  payload: Record<string, unknown>,
): StatePatch {
  const value = payload[key];
  return typeof value === "number" ? { [key]: value } : {};
}

function patchDeviceStatus(devices: Device[], payload: Record<string, unknown>): Device[] {
  const deviceId = payload.device_id;
  const status = payload.status;
  if (typeof deviceId !== "number" || typeof status !== "string") {
    return devices;
  }
  return devices.map((device) =>
    device.id === deviceId ? { ...device, status: status as Device["status"] } : device,
  );
}

function patchAutomation(
  state: HomeState,
  payload: Record<string, unknown>,
): HomeState["automation"] {
  const current = state.automation;
  const number = (key: string, fallback: number): number => {
    const value = payload[key];
    return typeof value === "number" ? value : fallback;
  };
  const flag = (key: string, fallback: boolean): boolean => {
    const value = payload[key];
    return typeof value === "boolean" ? value : fallback;
  };
  return {
    enabled: flag("enabled", current.enabled),
    target_temperature: number("target_temperature", current.target_temperature),
    min_temperature: number("min_temperature", current.min_temperature),
    max_temperature: number("max_temperature", current.max_temperature),
    target_humidity: number("target_humidity", current.target_humidity),
    min_humidity: number("min_humidity", current.min_humidity),
    max_humidity: number("max_humidity", current.max_humidity),
    participating_device_ids: Array.isArray(payload.participating_device_ids)
      ? (payload.participating_device_ids as number[])
      : current.participating_device_ids,
  };
}
