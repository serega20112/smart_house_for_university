/**
 * Состояние дома, которое общий хук держит актуальным.
 *
 * Пока сокет открыт, каждое изменение приходит событием и дописывается в уже
 * прочитанный снимок. Если сокет падает, хук переходит на опрос, чтобы экран не
 * показывал вчерашние числа, и перестаёт опрашивать, как только связь вернётся.
 */

import { useCallback, useEffect, useState } from "react";

import * as api from "../../services/api";
import { useRealtime, type ConnectionState } from "../../services/realtime";
import { getToken } from "../../services/session";
import type { HomeState } from "../../services/types";
import { needsReload, reduceEvent } from "./reducer";

const EMPTY_AUTOMATION: HomeState["automation"] = {
  enabled: false,
  target_temperature: 22,
  target_humidity: 45,
  temperature_tolerance: 1,
  humidity_tolerance: 5,
  participating_device_ids: [],
};

const INITIAL: HomeState = {
  board_online: false,
  automation_suspended: false,
  reading: { temperature: null, humidity: null },
  devices: [],
  automation: EMPTY_AUTOMATION,
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
 * Хранит снимок дома вошедшего аккаунта и держит его свежим.
 *
 * @returns Снимок текущего человека вместе с состоянием загрузки.
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
      // Отказ платы человек должен увидеть: чужие коды ошибок экрану не нужны.
      if (incoming.type === "board.error") {
        setError(typeof incoming.payload.message === "string" ? incoming.payload.message : null);
        return;
      }
      if (needsReload(incoming.type)) {
        void refresh();
        return;
      }
      setState((current) => {
        const patch = reduceEvent(current, incoming.type, incoming.payload);
        return Object.keys(patch).length > 0 ? { ...current, ...patch } : current;
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
