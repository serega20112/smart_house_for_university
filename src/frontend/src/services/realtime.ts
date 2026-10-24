/** Живые изменения, которые приносит WebSocket бэкенда. */

import { useCallback, useEffect, useRef, useState } from "react";

import { fetchRealtimeTicket } from "./api";
import { getToken } from "./session";
import type { RealtimeEvent } from "./types";

export interface RealtimeMessage {
  type: RealtimeEvent;
  payload: Record<string, unknown>;
}

export type ConnectionState = "connecting" | "open" | "closed";

const RECONNECT_MIN_MS = 1000;
const RECONNECT_MAX_MS = 10000;

interface RealtimeOptions {
  enabled: boolean;
  onMessage: (message: RealtimeMessage) => void;
  onStateChange?: (state: ConnectionState) => void;
}

/**
 * Подписывается на поток событий бэкенда и держит сокет живым.
 *
 * Бэкенд присылает каждое изменение того аккаунта, который вошёл, поэтому экран не
 * опрашивает сервер, пока сокет открыт. Поток открывается с одноразовым билетом, который
 * сервер меняет на аккаунт — именно это отдаёт события одного аккаунта, не светя токен
 * сессии в адресе соединения.
 *
 * @param options.enabled Есть ли вообще сессия, с которой стоит связываться.
 * @param options.onMessage Вызывается на каждое принятое событие.
 * @param options.onStateChange Вызывается при каждой смене состояния связи.
 * @returns Текущее состояние соединения.
 */
export function useRealtime({ enabled, onMessage, onStateChange }: RealtimeOptions): ConnectionState {
  const [connection, setConnection] = useState<ConnectionState>("connecting");
  const handler = useRef(onMessage);
  const stateHandler = useRef(onStateChange);
  handler.current = onMessage;
  stateHandler.current = onStateChange;

  const report = useCallback((next: ConnectionState) => {
    setConnection((current) => (current === next ? current : next));
    stateHandler.current?.(next);
  }, []);

  useEffect(() => {
    if (!enabled) {
      return;
    }
    let socket: WebSocket | null = null;
    let retry = RECONNECT_MIN_MS;
    let timer: number | undefined;
    let closed = false;

    const scheduleRetry = () => {
      timer = window.setTimeout(connect, retry);
      retry = Math.min(retry * 2, RECONNECT_MAX_MS);
    };

    const connect = () => {
      if (closed) {
        return;
      }
      if (!getToken()) {
        return;
      }
      report("connecting");
      void openWithTicket();
    };

    // Билет одноразовый, поэтому каждый заход просит у сервера новый, а не переиспользует старый.
    const openWithTicket = async () => {
      let ticket: string;
      try {
        ({ ticket } = await fetchRealtimeTicket());
      } catch {
        if (!closed) {
          scheduleRetry();
        }
        return;
      }
      if (closed) {
        return;
      }
      socket = openSocket(ticket);

      socket.onopen = () => {
        retry = RECONNECT_MIN_MS;
        report("open");
      };
      socket.onmessage = (raw) => {
        try {
          handler.current(JSON.parse(raw.data as string) as RealtimeMessage);
        } catch {
          return;
        }
      };
      socket.onclose = () => {
        report("closed");
        scheduleRetry();
      };
      socket.onerror = () => socket?.close();
    };

    connect();

    return () => {
      closed = true;
      if (timer !== undefined) {
        window.clearTimeout(timer);
      }
      socket?.close();
    };
  }, [enabled, report]);

  return connection;
}

/**
 * Открывает сокет события одного аккаунта: билет едет параметром строки запроса.
 *
 * Заголовок авторизации на handshake WebSocket повесить нельзя, поэтому адрес несёт
 * короткий одноразовый билет, который сервер меняет на аккаунт ровно один раз.
 *
 * @param ticket Одноразовый билет, выданный REST под текущей сессией.
 * @returns Соединение, которое вызывающий уже обслуживает сам.
 */
function openSocket(ticket: string): WebSocket {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  return new WebSocket(
    `${protocol}://${window.location.host}/ws?ticket=${encodeURIComponent(ticket)}`,
  );
}
