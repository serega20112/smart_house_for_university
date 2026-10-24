/**
 * Типизированный доступ к REST API бэкенда.
 *
 * Клиент знает только пути и формы: он кладёт токен в заголовок, разбирает ответ
 * и превращает отказ сервера в ошибку с человеческими словами. Никакого решения
 * о том, что разрешено и что из этого следует, здесь нет — этим занимается бэкенд.
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
  // Ответ без тела — законный исход: удаление или выход. Читать у него нечего.
  if (response.status === NO_CONTENT) {
    return undefined as T;
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

/**
 * Создаёт аккаунт и открывает для него сессию.
 *
 * @param payload Электронная почта, пароль и имя для интерфейса.
 * @returns Токен сессии и профиль нового аккаунта.
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
 * Авторизует аккаунт и выдаёт токен сессии.
 *
 * @param payload Электронная почта и пароль.
 * @returns Токен сессии и профиль вошедшего аккаунта.
 */
export function login(payload: { email: string; password: string }): Promise<Session> {
  return request<Session>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Закрывает текущую сессию.
 *
 * @returns Подтверждение выхода.
 */
export function logout(): Promise<OperationResult> {
  return request<OperationResult>("/auth/logout", { method: "POST" });
}

/**
 * Возвращает аккаунт текущей сессии.
 *
 * @returns Профиль вошедшего аккаунта.
 */
export function fetchProfile(): Promise<UserProfile> {
  return request<UserProfile>("/auth/me");
}

/**
 * Возвращает весь главный экран одним снимком.
 *
 * @returns Снимок дома текущего аккаунта.
 */
export function fetchHomeState(): Promise<HomeState> {
  return request<HomeState>("/state");
}

/**
 * Возвращает настроенные устройства с их текущим состоянием.
 *
 * @returns Устройства аккаунта.
 */
export function fetchDevices(): Promise<Device[]> {
  return request<Device[]>("/devices");
}

/**
 * Просит устройство выполнить способность.
 *
 * @param deviceId Идентификатор устройства.
 * @param capability Способность, которую нужно выполнить.
 * @returns Устройство в состоянии, которого оно достигло.
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
 * Регистрирует новое логическое устройство.
 *
 * @param payload Описание устройства.
 * @returns Созданное устройство.
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
 * Применяет частичное изменение устройства.
 *
 * @param deviceId Идентификатор устройства.
 * @param payload Поля, которые нужно изменить.
 * @returns Обновлённое устройство.
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
 * Удаляет устройство.
 *
 * @param deviceId Идентификатор устройства.
 * @returns Ничего: отказ сервера приходит исключением.
 */
export function deleteDevice(deviceId: string): Promise<void> {
  return request<void>(`/devices/${deviceId}`, { method: "DELETE" });
}

/**
 * Возвращает настройку автоматизации текущего аккаунта.
 *
 * @returns Настройка аккаунта.
 */
export function fetchAutomation(): Promise<Automation> {
  return request<Automation>("/automation");
}

/**
 * Применяет частичное изменение настройки автоматизации.
 *
 * @param payload Поля, которые нужно изменить.
 * @returns Настройка такой, какой она стала.
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
 * Возвращает все сценарии текущего аккаунта.
 *
 * @returns Сценарии аккаунта.
 */
export function fetchScenarios(): Promise<Scenario[]> {
  return request<Scenario[]>("/scenarios");
}

/**
 * Отменяет сценарий.
 *
 * @param scenarioId Идентификатор сценария.
 * @returns Отменённый сценарий.
 */
export function cancelScenario(scenarioId: string): Promise<Scenario> {
  return request<Scenario>(`/scenarios/${scenarioId}`, { method: "DELETE" });
}

/**
 * Возвращает настройки интерфейса вошедшего аккаунта.
 *
 * @returns Настройки такие, какие сохранены.
 */
export function fetchPreferences(): Promise<Preferences> {
  return request<Preferences>("/preferences");
}

/**
 * Применяет частичное изменение настроек интерфейса.
 *
 * @param payload Поля, которые человек хочет изменить.
 * @returns Настройки такими, какими они стали.
 */
export function updatePreferences(payload: Partial<Preferences>): Promise<Preferences> {
  return request<Preferences>("/preferences", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

/**
 * Возвращает раскладку главного экрана вошедшего аккаунта.
 *
 * @returns Виджеты в порядке вывода.
 */
export function fetchDashboard(): Promise<Dashboard> {
  return request<Dashboard>("/dashboard");
}

/**
 * Заменяет раскладку главного экрана целиком.
 *
 * @param widgets Виджеты в новом порядке.
 * @returns Сохранённая раскладка.
 */
export function updateDashboard(widgets: Widget[]): Promise<Dashboard> {
  return request<Dashboard>("/dashboard", {
    method: "PATCH",
    body: JSON.stringify({ widgets }),
  });
}

/**
 * Возвращает платы, сопряжённые с текущим аккаунтом.
 *
 * @returns Платы аккаунта с живой доступностью.
 */
export function fetchBoards(): Promise<Board[]> {
  return request<Board[]>("/esp-devices");
}

/**
 * Сопрягает плату и один раз показывает её ключ.
 *
 * @param payload Имя платы и, возможно, выбранный человеком ключ.
 * @returns Сопряжённая плата вместе с её ключом.
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
 * Возвращает платы, которые ждут, что их заберут.
 *
 * @returns Предложения с токеном, кодом и сроком.
 */
export function fetchBoardClaims(): Promise<BoardClaim[]> {
  return request<BoardClaim[]>("/esp-devices/claims");
}

/**
 * Забирает объявленную плату за текущим аккаунтом.
 *
 * @param payload Токен предложения и выбранное имя платы.
 * @returns Плата, которая теперь сопряжена.
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
 * Убирает плату из текущего аккаунта.
 *
 * @param boardId Идентификатор платы.
 * @returns Ничего: плата удалена, и показывать там нечего.
 */
export function revokeBoard(boardId: string): Promise<void> {
  return request<void>(`/esp-devices/${boardId}`, { method: "DELETE" });
}

/**
 * Возвращает сеть, которую предписано использовать плате.
 *
 * @param boardId Идентификатор платы.
 * @returns Сеть платы.
 */
export function fetchBoardNetwork(boardId: string): Promise<BoardNetwork> {
  return request<BoardNetwork>(`/esp-devices/${boardId}/network`);
}

/**
 * Сообщает плате сеть, которую та должна использовать.
 *
 * @param boardId Идентификатор платы.
 * @param payload Сеть, которую должна использовать плата.
 * @returns Сеть такой, какой она сохранена.
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
 * Отправляет написанную команду и возвращает то, что она дала.
 *
 * @param text Предложение таким, каким его ввели.
 * @returns Ответ на команду.
 */
export function sendCommand(text: string): Promise<CommandResult> {
  return request<CommandResult>("/commands", { method: "POST", body: JSON.stringify({ text }) });
}
