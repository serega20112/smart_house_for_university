/**
 * Typed access to the REST API backend.
 *
 * The client knows only paths and forms: it puts the token in the header
 * and turns server refusal into an error with human-friendly words. No logic
 * o what is allowed and what follows from it here — that is the backend's job.
 */

import type {
  Automation,
  Board,
  BoardClaim,
  BoardNetwork,
  Capability,
  CommandResult,
  Dashboard,
  Device,
  DeviceKind,
  HomeState,
  OperationResult,
  PairedBoard,
  Preferences,
  Scenario,
  Session,
  UserProfile,
  Widget,
} from "./types";
import { getToken, unauthorized } from "./session";

const BASE = "/api";
const NO_CONTENT = 204;

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
  // Response without body is a valid outcome: deletion or logout. Nothing to read.
  if (response.status === NO_CONTENT) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

async function errorText(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Request completed with code ${response.status}`;
  } catch {
    return `Request completed with code ${response.status}`;
  }
}

/**
 * Creates an account and opens a session for it.
 *
 * @param payload Email, password and display name for the interface.
 * @returns Session token and new account profile.
 */
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

/**
 * Authorizes an account and issues a session token.
 *
 * @param payload Email and password.
 * @returns Session token and logged-in account profile.
 */
export function login(payload: { email: string; password: string }): Promise<Session> {
  return request<Session>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Closes the current session.
 *
 * @returns Logout confirmation.
 */
export function logout(): Promise<OperationResult> {
  return request<OperationResult>("/auth/logout", { method: "POST" });
}

/**
 * Returns the account of the current session.
 *
 * @returns Logged-in account profile.
 */
export function fetchProfile(): Promise<UserProfile> {
  return request<UserProfile>("/auth/me");
}

/**
 * Requests a one-time ticket to open the event stream WebSocket.
 *
 * Session token does not travel in the socket address: REST over the current session issues a short ticket,
 * which the server exchanges for an account exactly once.
 *
 * @returns Ticket and its lifetime in seconds.
 */
export function fetchRealtimeTicket(): Promise<{ ticket: string; expires_in_sec: number }> {
  return request<{ ticket: string; expires_in_sec: number }>("/auth/realtime-ticket", {
    method: "POST",
  });
}

/**
 * Returns the whole home screen in one snapshot.
 *
 * @returns Snapshot of the current account home.
 */
export function fetchHomeState(): Promise<HomeState> {
  return request<HomeState>("/state");
}

/**
 * Returns configured devices with their current state.
 *
 * @returns Account devices.
 */
export function fetchDevices(): Promise<Device[]> {
  return request<Device[]>("/devices");
}

/**
 * Asks a device to perform a capability.
 *
 * @param deviceId Device identifier.
 * @param capability Capability to perform.
 * @returns Device in the state it reached.
 */
export function performCapability(
  deviceId: string,
  capability: Capability,
): Promise<Device> {
  return request<Device>(`/devices/${deviceId}/capabilities/${capability}`, {
    method: "POST",
  });
}

/**
 * Registers a new logical device.
 *
 * @param payload Device description.
 * @returns Created device.
 */
export function createDevice(payload: {
  name: string;
  kind: DeviceKind;
  channel: number;
  capabilities: Capability[];
  enabled?: boolean;
  automation_enabled?: boolean;
}): Promise<Device> {
  return request<Device>("/devices", { method: "POST", body: JSON.stringify(payload) });
}

/**
 * Applies a partial device change.
 *
 * @param deviceId Device identifier.
 * @param payload Fields to change.
 * @returns Updated device.
 */
export function updateDevice(
  deviceId: string,
  payload: Partial<{
    name: string;
    kind: DeviceKind;
    channel: number;
    capabilities: Capability[];
    enabled: boolean;
    automation_enabled: boolean;
  }>,
): Promise<Device> {
  return request<Device>(`/devices/${deviceId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

/**
 * Deletes a device.
 *
 * @param deviceId Device identifier.
 * @returns Nothing: server refusal arrives as an exception.
 */
export function deleteDevice(deviceId: string): Promise<void> {
  return request<void>(`/devices/${deviceId}`, { method: "DELETE" });
}

/**
 * Returns the automation settings of the current account.
 *
 * @returns Account settings.
 */
export function fetchAutomation(): Promise<Automation> {
  return request<Automation>("/automation");
}

/**
 * Applies a partial change to automation settings.
 *
 * @param payload Fields to change.
 * @returns Settings as they became.
 */
export function updateAutomation(payload: Partial<{
  enabled: boolean;
  target_temperature: number;
  temperature_tolerance: number;
  target_humidity: number;
  humidity_tolerance: number;
  participating_device_ids: string[];
}>): Promise<Automation> {
  return request<Automation>("/automation", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

/**
 * Returns all scenarios of the current account.
 *
 * @returns Account scenarios.
 */
export function fetchScenarios(): Promise<Scenario[]> {
  return request<Scenario[]>("/scenarios");
}

/**
 * Cancels a scenario.
 *
 * @param scenarioId Scenario identifier.
 * @returns Cancelled scenario.
 */
export function cancelScenario(scenarioId: string): Promise<Scenario> {
  return request<Scenario>(`/scenarios/${scenarioId}`, { method: "DELETE" });
}

/**
 * Returns the interface settings of the logged-in account.
 *
 * @returns Settings as saved.
 */
export function fetchPreferences(): Promise<Preferences> {
  return request<Preferences>("/preferences");
}

/**
 * Applies a partial change to interface settings.
 *
 * @param payload Fields the person wants to change.
 * @returns Settings as they became.
 */
export function updatePreferences(payload: Partial<Preferences>): Promise<Preferences> {
  return request<Preferences>("/preferences", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

/**
 * Returns the dashboard layout of the logged-in account.
 *
 * @returns Widgets in display order.
 */
export function fetchDashboard(): Promise<Dashboard> {
  return request<Dashboard>("/dashboard");
}

/**
 * Replaces the dashboard layout entirely.
 *
 * @param widgets Widgets in new order.
 * @returns Saved layout.
 */
export function updateDashboard(widgets: Widget[]): Promise<Dashboard> {
  return request<Dashboard>("/dashboard", {
    method: "PATCH",
    body: JSON.stringify({ widgets }),
  });
}

/**
 * Returns boards paired with the current account.
 *
 * @returns Account boards with live availability.
 */
export function fetchBoards(): Promise<Board[]> {
  return request<Board[]>("/esp-devices");
}

/**
 * Pairs a board and shows its key once.
 *
 * @param payload Board name and, possibly, a key chosen by the person.
 * @returns Paired board together with its key.
 */
export function pairBoard(payload: {
  name: string;
  pairing_key?: string;
}): Promise<PairedBoard> {
  return request<PairedBoard>("/esp-devices", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Returns boards waiting to be claimed.
 *
 * @returns Offers with token, code and expiry.
 */
export function fetchBoardClaims(): Promise<BoardClaim[]> {
  return request<BoardClaim[]>("/esp-devices/claims");
}

/**
 * Claims a declared board for the current account.
 *
 * @param payload Offer token and chosen board name.
 * @returns Board that is now paired.
 */
export function claimBoard(payload: {
  claim_token: string;
  name: string;
}): Promise<Board> {
  return request<Board>("/esp-devices/claims", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Removes a board from the current account.
 *
 * @param boardId Board identifier.
 * @returns Nothing: board is removed, nothing to show.
 */
export function revokeBoard(boardId: string): Promise<void> {
  return request<void>(`/esp-devices/${boardId}`, { method: "DELETE" });
}

/**
 * Returns the network the board is prescribed to use.
 *
 * @param boardId Board identifier.
 * @returns Board network.
 */
export function fetchBoardNetwork(boardId: string): Promise<BoardNetwork> {
  return request<BoardNetwork>(`/esp-devices/${boardId}/network`);
}

/**
 * Tells the board the network it should use.
 *
 * @param boardId Board identifier.
 * @param payload Network the board should use.
 * @returns Network as saved.
 */
export function updateBoardNetwork(
  boardId: string,
  payload: {
    ssid: string;
    password: string;
    host: string;
    server_port: number;
    socket_port: number;
    socket_path: string;
  },
): Promise<BoardNetwork> {
  return request<BoardNetwork>(`/esp-devices/${boardId}/network`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

/**
 * Sends a written command and returns what it produced.
 *
 * @param text Sentence as entered.
 * @returns Command response.
 */
export function sendCommand(text: string): Promise<CommandResult> {
  return request<CommandResult>("/commands", { method: "POST", body: JSON.stringify({ text }) });
}
