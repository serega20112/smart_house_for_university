/**
 * Живой снимок дома.
 *
 * Единственный источник правды о текущем состоянии — REST: сервер держит его в базе и
 * Redis, а браузер читает одним запросом. События потока не привносят в экран собственные
 * числа, а только говорят «изменилось, перечитай»: так интерфейс не может показать то,
 * чего сервер не говорил.
 *
 * Пачка событий за секунду сливается в один запрос — иначе щелчок по кнопке вызвал бы
 * пять чтений подряд.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import * as api from "@/shared/api/client";
import { useRealtime, type ConnectionState } from "@/shared/realtime/use-realtime";
import type { HomeState } from "@/shared/api/types";

/** Сколько миллисекунд ждём, прежде чем перечитать дом после события. */
const MERGE_WINDOW_MS = 250;

/** Чем хук делится с экраном. */
export interface HomeStateStore {
  state: HomeState | null;
  loading: boolean;
  error: string | null;
  connection: ConnectionState;
  syncedAt: number | null;
  refresh: () => Promise<void>;
}

/**
 * Читает состояние дома и держит его свежим.
 *
 * @returns Снимок, признаки загрузки и отказа, состояние потока событий и способ
 *   перечитать всё вручную.
 */
export function useHomeState(): HomeStateStore {
  const [state, setState] = useState<HomeState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncedAt, setSyncedAt] = useState<number | null>(null);
  const timer = useRef<number | null>(null);

  const load = useCallback(async () => {
    try {
      setState(await api.fetchHomeState());
      setError(null);
      setSyncedAt(Date.now());
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Состояние дома не прочиталось");
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Ставит перечитывание на ближайший свободный момент.
   */
  const onEvent = useCallback(() => {
    if (timer.current !== null) {
      return;
    }
    timer.current = window.setTimeout(() => {
      timer.current = null;
      void load();
    }, MERGE_WINDOW_MS);
  }, [load]);

  const connection = useRealtime(onEvent);

  // Соединение упало и поднялось: за время паузы события могли пройти мимо — читаем снова.
  useEffect(() => {
    if (connection === "open") {
      void load();
    }
  }, [connection, load]);

  useEffect(
    () => () => {
      if (timer.current !== null) {
        window.clearTimeout(timer.current);
        timer.current = null;
      }
    },
    [],
  );

  useEffect(() => {
    void load();
  }, [load]);

  return { state, loading, error, connection, syncedAt, refresh: load };
}
