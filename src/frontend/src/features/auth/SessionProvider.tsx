/**
 * Session of the browser.
 *
 * The provider owns exactly one question: who is signed in. Everything the
 * interface renders afterwards comes from the API using that session, which is
 * what keeps one build serving many accounts.
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

import * as api from "../../services/api";
import { getToken, onUnauthorized, onSessionChange, setToken, clearToken } from "../../services/session";
import type { Preferences, Session, UserProfile } from "../../services/types";

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
 * Provides the current session to the whole application.
 *
 * @param props.children Rendered subtree.
 */
export function SessionProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [preferences, setPreferences] = useState<Preferences | null>(null);
  const [ready, setReady] = useState(false);

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
 * Reads the session from the context.
 *
 * @returns The session store of the current browser.
 */
export function useSession(): SessionStore {
  const store = useContext(SessionContext);
  if (!store) {
    throw new Error("useSession must be used inside a SessionProvider");
  }
  return store;
}
