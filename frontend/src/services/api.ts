/** Typed access to the backend REST API. */

import type {
  Automation,
  BoardNetwork,
  Capability,
  CommandResult,
  Dashboard,
  Device,
  DeviceStatus,
  DeviceType,
  EspClaim,
  EspDevice,
  ExecutionResult,
  HomeState,
  Preferences,
  Scenario,
  Session,
  SettingsResult,
  UserProfile,
  Widget,
} from "./types";
import { getToken, unauthorized } from "./session";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
      ...init?.headers,
    },
  });
  if (response.status === 401) {
    unauthorized();
  }
  if (!response.ok) {
    throw new Error(await errorText(response));
  }
  return (await response.json()) as T;
}

async function errorText(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Запрос завершился с кодом ${response.status}`;
  } catch {
    return `Запрос завершился с кодом ${response.status}`;
  }
}

export function register(payload: {
  email: string;
  password: string;
  display_name: string;
}): Promise<Session> {
  return request<Session>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function login(payload: { email: string; password: string }): Promise<Session> {
  return request<Session>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function logout(): Promise<{ status: string }> {
  return request<{ status: string }>("/auth/logout", { method: "POST" });
}

export function fetchProfile(): Promise<UserProfile> {
  return request<UserProfile>("/auth/me");
}

export function fetchHomeState(): Promise<HomeState> {
  return request<HomeState>("/state");
}

export function fetchDevices(): Promise<Device[]> {
  return request<Device[]>("/devices");
}

export function fetchAutomation(): Promise<Automation> {
  return request<Automation>("/automation");
}

export function fetchScenarios(): Promise<Scenario[]> {
  return request<Scenario[]>("/scenarios");
}

export function fetchPreferences(): Promise<Preferences> {
  return request<Preferences>("/preferences");
}

export function updatePreferences(payload: Partial<Preferences>): Promise<unknown> {
  return request("/preferences", { method: "PATCH", body: JSON.stringify(payload) });
}

export function fetchDashboard(): Promise<Dashboard> {
  return request<Dashboard>("/dashboard");
}

export function updateDashboard(widgets: Widget[]): Promise<unknown> {
  return request("/dashboard", {
    method: "PATCH",
    body: JSON.stringify({ widgets }),
  });
}

export function fetchEspDevices(): Promise<EspDevice[]> {
  return request<EspDevice[]>("/esp-devices");
}

export function pairEspDevice(payload: {
  name: string;
  pairing_key?: string;
}): Promise<{ status: string; message: string; data: EspDevice }> {
  return request("/esp-devices", { method: "POST", body: JSON.stringify(payload) });
}

export function fetchEspClaims(): Promise<EspClaim[]> {
  return request<EspClaim[]>("/esp-devices/claims");
}

export function claimEspDevice(payload: {
  claim_token: string;
  name: string;
}): Promise<{ status: string; message: string }> {
  return request("/esp-devices/claims", { method: "POST", body: JSON.stringify(payload) });
}

export function unpairEspDevice(deviceId: string): Promise<{ status: string; message: string }> {
  return request(`/esp-devices/${deviceId}`, { method: "DELETE" });
}

export function fetchBoardNetwork(deviceId: string): Promise<BoardNetwork | null> {
  return request<BoardNetwork | null>(`/esp-devices/${deviceId}/network`);
}

export function updateBoardNetwork(
  deviceId: string,
  payload: {
    ssid: string;
    password: string;
    host: string;
    server_port: number;
    socket_port: number;
    socket_path: string;
  },
): Promise<BoardNetwork> {
  return request<BoardNetwork>(`/esp-devices/${deviceId}/network`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function turnDeviceOn(deviceId: number): Promise<ExecutionResult> {
  return request<ExecutionResult>(`/devices/${deviceId}/on`, { method: "POST" });
}

export function turnDeviceOff(deviceId: number): Promise<ExecutionResult> {
  return request<ExecutionResult>(`/devices/${deviceId}/off`, { method: "POST" });
}

export function setDeviceMode(
  deviceId: number,
  mode: Capability,
): Promise<ExecutionResult> {
  return request<ExecutionResult>(`/devices/${deviceId}/mode`, {
    method: "POST",
    body: JSON.stringify({ mode }),
  });
}

export function createDevice(payload: {
  name: string;
  type: DeviceType;
  physical_channel: number;
  capabilities: Capability[];
  automation_enabled: boolean;
}): Promise<{ status: string; message: string; data: Device }> {
  return request("/devices", { method: "POST", body: JSON.stringify(payload) });
}

export function updateDevice(
  deviceId: number,
  payload: Partial<{
    name: string;
    type: DeviceType;
    physical_channel: number;
    capabilities: Capability[];
    enabled: boolean;
    automation_enabled: boolean;
  }>,
): Promise<{ status: string; message: string; data: Device }> {
  return request(`/devices/${deviceId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteDevice(
  deviceId: number,
): Promise<{ status: string; message: string }> {
  return request(`/devices/${deviceId}`, { method: "DELETE" });
}

export interface AutomationUpdate {
  enabled?: boolean;
  target_temperature?: number;
  temperature_tolerance?: number;
  target_humidity?: number;
  humidity_tolerance?: number;
  participating_device_ids?: number[];
}

export function updateAutomation(payload: AutomationUpdate): Promise<SettingsResult> {
  return request("/automation", { method: "PUT", body: JSON.stringify(payload) });
}

export function setAutomationEnabled(enabled: boolean): Promise<SettingsResult> {
  return request(`/automation/${enabled ? "enable" : "disable"}`, { method: "POST" });
}

export function cancelScenario(
  scenarioId: number,
): Promise<{ status: string; message: string }> {
  return request(`/scenarios/${scenarioId}`, { method: "DELETE" });
}

export function sendCommand(text: string): Promise<CommandResult> {
  return request("/commands", { method: "POST", body: JSON.stringify({ text }) });
}

export const statusOrder: Record<DeviceStatus, number> = {
  COOL: 0,
  HEAT: 1,
  ON: 2,
  OFF: 3,
  UNAVAILABLE: 4,
};
