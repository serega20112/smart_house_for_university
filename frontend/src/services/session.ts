/**
 * Storage of the session token.
 *
 * The token is the only thing proving who the browser is, so it is kept in one
 * module: the API client and the event stream both read it from here and both
 * forget it the moment the backend rejects it.
 */

const STORAGE_KEY = "smart-home.token";

type Listener = () => void;

const listeners = new Set<Listener>();
const unauthorizedListeners = new Set<Listener>();

/**
 * Returns the token of the current session.
 *
 * @returns The stored token, or null when the visitor is signed out.
 */
export function getToken(): string | null {
  return window.localStorage.getItem(STORAGE_KEY);
}

/**
 * Stores the token issued by the backend.
 *
 * @param token Token returned by registration or login.
 */
export function setToken(token: string): void {
  window.localStorage.setItem(STORAGE_KEY, token);
  notify();
}

/**
 * Forgets the current token and tells the application about it.
 */
export function clearToken(): void {
  window.localStorage.removeItem(STORAGE_KEY);
  notify();
}

/**
 * Registers a callback fired whenever the session changes.
 *
 * @param listener Callback to invoke on every session change.
 *
 * @returns A function removing the callback again.
 */
export function onSessionChange(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/**
 * Registers a callback fired when the backend refuses the stored token.
 *
 * @param listener Callback to invoke on an unauthorized answer.
 *
 * @returns A function removing the callback again.
 */
export function onUnauthorized(listener: Listener): () => void {
  unauthorizedListeners.add(listener);
  return () => unauthorizedListeners.delete(listener);
}

/**
 * Drops the session after the backend refused the stored token.
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
