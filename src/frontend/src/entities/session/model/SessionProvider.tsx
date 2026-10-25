/**
 * Сессия браузера.
 *
 * Провайдер отвечает ровно на один вопрос: кто вошёл. Всё остальное интерфейс
 * получает через API под этой сессией, поэтому одна сборка служит многим аккаунтам.
 *
 * Настройки аккаунта читаются вместе с профилем: они определяют, как экран красится,
 * и не должны подтягиваться втихую где-нибудь внизу страницы.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import * as api from "@/shared/api/client";
import { clearToken, getToken, onSessionChange, onUnauthorized, setToken } from "@/shared/lib/token";
import type { Preferences, Session, UserProfile } from "@/shared/api/types";

/** Что провайдер знает об аккаунте и что умеет. */
export interface SessionStore {
  profile: UserProfile | null;
  preferences: Preferences | null;
  ready: boolean;
  signIn: (session: Session) => void;
  signOut: () => void;
  refreshPreferences: () => Promise<void>;
}

const SessionContext = createContext<SessionStore | null>(null);

/**
 * Отдаёт текущую сессию всей программе.
 *
 * @param props.children Поддерево, которое видит сессию.
 * @returns Провайдер сессии.
 */
export function SessionProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [preferences, setPreferences] = useState<Preferences | null>(null);
  const [ready, setReady] = useState(false);

  /**
   * Читает профиль и настройки под сохранённым токеном.
   *
   * Отказ сервера означает одно: сессии больше нет. Профиль забывается, и человек
   * видит экран входа, а не пустой дом с чужим токеном в адресной строке.
   */
  const load = useCallback(async () => {
    if (!getToken()) {
      setProfile(null);
      setPreferences(null);
      setReady(true);
      return;
    }
    try {
      setProfile(await api.fetchProfile());
      setPreferences(await api.fetchPreferences());
    } catch {
      setProfile(null);
      setPreferences(null);
    } finally {
      setReady(true);
    }
  }, []);

  const refreshPreferences = useCallback(async () => {
    try {
      setPreferences(await api.fetchPreferences());
    } catch {
      setPreferences(null);
    }
  }, []);

  useEffect(() => {
    void load();
    return onSessionChange(() => void load());
  }, [load]);

  useEffect(() => onUnauthorized(() => setProfile(null)), []);

  const signIn = useCallback((session: Session) => {
    setToken(session.access_token);
    setProfile(session.user);
  }, []);

  const signOut = useCallback(() => {
    void api.logout().catch(() => undefined);
    clearToken();
    setProfile(null);
    setPreferences(null);
  }, []);

  const value = useMemo<SessionStore>(
    () => ({ profile, preferences, ready, signIn, signOut, refreshPreferences }),
    [profile, preferences, ready, signIn, signOut, refreshPreferences],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

/**
 * Читает сессию из контекста.
 *
 * @returns Хранилище сессии текущего браузера.
 */
export function useSession(): SessionStore {
  const store = useContext(SessionContext);
  if (!store) {
    throw new Error("useSession можно вызывать только внутри SessionProvider");
  }
  return store;
}
