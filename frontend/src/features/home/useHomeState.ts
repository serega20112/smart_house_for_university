/** Shared home state kept live by the backend event stream. */

import { useCallback, useEffect, useState } from "react";

import * as api from "../../services/api";
import { useRealtime, type ConnectionState } from "../../services/realtime";
import { getToken } from "../../services/session";
import type { HomeState } from "../../services/types";
import { needsReload, reduceEvent } from "./reducer";

const INITIAL: HomeState = {
  backend_online: true,
  esp_online: false,
  manual_override: false,
  temperature: null,
  humidity: null,
  devices: [],
  automation: {
    enabled: false,
    target_temperature: 22,
    min_temperature: 21,
    max_temperature: 23,
    target_humidity: 45,
    min_humidity: 40,
    max_humidity: 50,
    participating_device_ids: [],
  },
  active_scenarios: [],
};

const FALLBACK_POLL_MS = 5000;

export interface HomeStore {
  state: HomeState;
  loading: boolean;
  error: string | null;
  connection: ConnectionState;
  refresh: () => Promise<void>;
}

/**
 * Holds the home snapshot of the signed in account and keeps it current.
 *
 * While the WebSocket is open every change arrives as an event and is applied
 * in place. If the socket drops, the store falls back to polling so the
 * interface never shows stale data, and stops polling once it is back.
 *
 * @returns The snapshot of the current user together with its load state.
 */
export function useHomeState(): HomeStore {
  const [state, setState] = useState<HomeState>(INITIAL);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!getToken()) {
      return;
    }
    try {
      setState(await api.fetchHomeState());
      setError(null);
    } catch (exc) {
      setError(message(exc));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const realtimeState = useRealtime({
    enabled: Boolean(getToken()),
    onMessage: (incoming) => {
      if (needsReload(incoming.type)) {
        void refresh();
        return;
      }
      setState((current) => {
        const patch = reduceEvent(current, incoming.type, incoming.payload);
        return patch ? { ...current, ...patch } : current;
      });
    },
  });

  useEffect(() => {
    if (realtimeState !== "closed") {
      return;
    }
    const timer = window.setInterval(() => {
      void refresh();
    }, FALLBACK_POLL_MS);
    return () => window.clearInterval(timer);
  }, [realtimeState, refresh]);

  useEffect(() => {
    if (realtimeState === "open") {
      void refresh();
    }
  }, [realtimeState, refresh]);

  return { state, loading, error, connection: realtimeState, refresh };
}

function message(exc: unknown): string {
  return exc instanceof Error ? exc.message : "Не удалось получить состояние дома";
}
