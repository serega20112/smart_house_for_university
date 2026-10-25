/**
 * Типизированный доступ к REST API бэкенда.
 *
 * Клиент знает только пути и формы: он подставляет токен в заголовок и превращает
 * отказ сервера в ошибку с человеческими словами. Логики о том, что разрешено и что
 * из этого следует, здесь нет — это дело бэкенда.
 *
 * Каждый путь ниже сверен с `presentation/api/v1`: лишний параметр сервер отвергает
 * (модели строгой схемы), поэтому угадывать состав тела нельзя.
 */

import type {
  Automation,
  Board,
  BoardClaim,
  BoardNetwork,
  Capability,
  CommandResult,
  CompletionBehavior,
  Dashboard,
  Device,
  DeviceKind,
  HomeState,
  OperationResult,
  Preferences,
  RealtimeTicket,
  Scenario,
  Session,
  UserProfile,
} from "@/shared/api/types";
import { getToken, unauthorized } from "@/shared/lib/token";

const BASE = "/api";
const NO_CONTENT = 204;

/**
 * Отказ сервера с кодом и человеческим текстом.
 *
 * Код нужен вызывающей стороне: отказ «не понял фразу» и отказ «нет соединения» выглядят
 * для человека по-разному, хотя оба приходят исключением.
 */
export class ApiError extends Error {
  readonly status: number;

  /**
   * Инициализирует отказ.
   *
   * @param status Код HTTP ответа.
   * @param message Текст, который прислал сервер.
   */
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  });
  if (response.status === 401) {
    unauthorized();
  }
  if (!response.ok) {
    throw new ApiError(response.status, await errorText(response));
  }
  // Ответ без тела — нормальный исход: удаление или выход. Читать нечего.
  if (response.status === NO_CONTENT) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

/**
 * Возвращает текст отказа так, как его написал бэкенд.
 *
 * @param response Ответ с кодом 4xx или 5xx.
 * @returns Строка, которую можно показать человеку.
 */
async function errorText(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: string };
    return payload.detail ?? `Запрос завершился с кодом ${response.status}`;
  } catch {
    return `Запрос завершился с кодом ${response.status}`;
  }
}

/* --- Сессия --------------------------------------------------------------- */

/**
 * Создаёт аккаунт и открывает для него сессию.
 *
 * @param payload Почта, пароль и имя, которое покажет интерфейс.
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
 * @param payload Почта и пароль.
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
 * Запрашивает одноразовый билет, чтобы открыть WebSocket потока событий.
 *
 * Токен сессии не ездит в адресе сокета: REST под текущей сессией выдаёт короткий
 * билет, который сервер обменивает на аккаунт ровно один раз.
 *
 * @returns Билет и время его жизни в секундах.
 */
export function fetchRealtimeTicket(): Promise<RealtimeTicket> {
  return request<RealtimeTicket>("/auth/realtime-ticket", { method: "POST" });
}

/* --- Дом ------------------------------------------------------------------ */

/**
 * Возвращает весь главный экран одним снимком.
 *
 * @returns Снимок дома текущего аккаунта.
 */
export function fetchHomeState(): Promise<HomeState> {
  return request<HomeState>("/state");
}

/* --- Устройства ----------------------------------------------------------- */

/**
 * Возвращает настроенные устройства вместе с их текущим состоянием.
 *
 * @returns Устройства аккаунта.
 */
export function fetchDevices(): Promise<Device[]> {
  return request<Device[]>("/devices");
}

/**
 * Заводит новое логическое устройство.
 *
 * @param payload Описание устройства, включая плату, если их несколько.
 * @returns Созданное устройство.
 */
export function createDevice(payload: {
  name: string;
  kind: DeviceKind;
  channel: number;
  capabilities: Capability[];
  enabled?: boolean;
  automation_enabled?: boolean;
  board_id?: string | null;
}): Promise<Device> {
  return request<Device>("/devices", { method: "POST", body: JSON.stringify(payload) });
}

/**
 * Применяет частичное изменение устройства.
 *
 * @param deviceId Идентификатор устройства.
 * @param payload Поля, которые нужно поменять.
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
    board_id: string | null;
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

/* --- Автоматизация -------------------------------------------------------- */

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
 * @param payload Поля, которые нужно поменять.
 * @returns Настройка в том виде, каким она стала.
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

/* --- Сценарии ------------------------------------------------------------- */

/**
 * Возвращает все сценарии текущего аккаунта, включая уже завершённые.
 *
 * @returns Сценарии аккаунта.
 */
export function fetchScenarios(): Promise<Scenario[]> {
  return request<Scenario[]>("/scenarios");
}

/**
 * Ставит отложенное действие в расписание дома.
 *
 * @param payload Действие, срок начала и поведение после завершения.
 * @returns Сценарий в том виде, каким он сохранился.
 */
export function scheduleScenario(payload: {
  capability: Capability;
  delay_minutes?: number | null;
  target?: string | null;
  target_temperature?: number | null;
  completion_behavior?: CompletionBehavior;
  duration_minutes?: number | null;
}): Promise<Scenario> {
  return request<Scenario>("/scenarios", { method: "POST", body: JSON.stringify(payload) });
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

/* --- Персональные настройки ------------------------------------------------ */

/**
 * Возвращает настройки интерфейса вошедшего аккаунта.
 *
 * @returns Настройки в том виде, в каком они сохранены.
 */
export function fetchPreferences(): Promise<Preferences> {
  return request<Preferences>("/preferences");
}

/**
 * Применяет частичное изменение настроек интерфейса.
 *
 * @param payload Поля, которые хочет поменять человек.
 * @returns Настройки в том виде, каким они стали.
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
 * Раскладка только читается: на каждое устройство сервер сам дописывает плитку, поэтому
 * менять её руками из интерфейса нечего.
 *
 * @returns Виджеты в порядке показа.
 */
export function fetchDashboard(): Promise<Dashboard> {
  return request<Dashboard>("/dashboard");
}

/* --- Платы ---------------------------------------------------------------- */

/**
 * Возвращает платы, сопряжённые с текущим аккаунтом.
 *
 * @returns Платы аккаунта с живой доступностью.
 */
export function fetchBoards(): Promise<Board[]> {
  return request<Board[]>("/esp-devices");
}

/**
 * Возвращает платы, которые ждут хозяина.
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
 * @returns Ничего: плата убрана, показывать нечего.
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
 * @returns Сеть в том виде, в каком она сохранена.
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

/* --- Команды -------------------------------------------------------------- */

/**
 * Отправляет написанную команду и возвращает, из чего она вышла.
 *
 * @param text Фраза так, как её ввёл человек.
 * @returns Ответ на команду.
 */
export function sendCommand(text: string): Promise<CommandResult> {
  return request<CommandResult>("/commands", { method: "POST", body: JSON.stringify({ text }) });
}
