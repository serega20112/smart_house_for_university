/** Live updates delivered by the backend WebSocket. */

import { useCallback, useEffect, useRef, useState } from "react";

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
 * Subscribes to the backend event stream and keeps the socket alive.
 *
 * The backend pushes every change of the signed in account, so the interface
 * never polls while the socket is open. The stream is opened with the session
 * token, which is what lets the server deliver only the events of this account.
 *
 * @param options.activates Whether a session is available at all.
 * @param options.onMessage Called for every received event.
 * @param options.onStateChange Called whenever the connection state changes.
 *
 * @returns The current connection state.
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

    const connect = () => {
      if (closed) {
        return;
      }
      const token = getToken();
      if (!token) {
        return;
      }
      report("connecting");
      socket = openSocket(token);

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
        timer = window.setTimeout(connect, retry);
        retry = Math.min(retry * 2, RECONNECT_MAX_MS);
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

function openSocket(token: string): WebSocket {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  return new WebSocket(
    `${protocol}://${window.location.host}/ws?token=${encodeURIComponent(token)}`,
  );
}
