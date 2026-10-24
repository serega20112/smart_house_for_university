/**
 * Хранилище токена сессии.
 *
 * Токен — единственное, что говорит серверу, кто этот браузер, поэтому он живёт в
 * одном модуле: клиент API и поток событий читают его отсюда и забывают о нём в тот
 * момент, когда бэкенд перестаёт его принимать.
 */

const STORAGE_KEY = "smart-home.token";

type Listener = () => void;

const listeners = new Set<Listener>();
const unauthorizedListeners = new Set<Listener>();

/**
 * Возвращает токен текущей сессии.
 *
 * @returns Сохранённый токен или None, когда гость вышел.
 */
export function getToken(): string | null {
  return window.localStorage.getItem(STORAGE_KEY);
}

/**
 * Запоминает токен, который выдал бэкенд.
 *
 * @param token Токен, пришедший после регистрации или входа.
 */
export function setToken(token: string): void {
  window.localStorage.setItem(STORAGE_KEY, token);
  notify();
}

/**
 * Забывает текущий токен и сообщает об этом программе.
 */
export function clearToken(): void {
  window.localStorage.removeItem(STORAGE_KEY);
  notify();
}

/**
 * Ставит слушателя, который срабатывает на каждую смену сессии.
 *
 * @param listener Функция, вызываемая при смене сессии.
 * @returns Функция, которая снимает слушателя.
 */
export function onSessionChange(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/**
 * Ставит слушателя, который срабатывает, когда сервер отверг сохранённый токен.
 *
 * @param listener Функция, вызываемая на отказ авторизации.
 * @returns Функция, которая снимает слушателя.
 */
export function onUnauthorized(listener: Listener): () => void {
  unauthorizedListeners.add(listener);
  return () => unauthorizedListeners.delete(listener);
}

/**
 * Сбрасывает сессию после того, как сервер отверг сохранённый токен.
 */
export function unauthorized(): void {
  if (!getToken()) {
    return;
  }
  clearToken();
  for (const listener of unauthorizedListeners) {
    listener();
  }
}

function notify(): void {
  for (const listener of listeners) {
    listener();
  }
}
