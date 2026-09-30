/** Live updates delivered by the backend WebSocket. */

import { useCallback, useEffect, useRef, useState } from "react";

import type { RealtimeEvent } from "./types";

export interface RealtimeMessage {
  type: RealtimeEvent;
  payload: Record<string, unknown>;
}

export type ConnectionState = "connecting" | "open" | "closed";

const RECONNECT_MIN_MS = 1000;
const RECONNECT_MAX_MS = 10000;

interface RealtimeOptions {
  onMessage: (message: RealtimeMessage) => void;
  onStateChange?: (state: ConnectionState) => void;
}

/**
 * Subscribes to the backend event stream and keeps the socket alive.
 *
 * The backend pushes every change, so the interface never polls while the
 * socket is open. When the socket is down the caller is told about it and may
 * fall back to polling until the connection is restored.
 */
export function useRealtime({ onMessage, onStateChange }: RealtimeOptions): ConnectionState {
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
    let socket: WebSocket | null = null;
    let retry = RECONNECT_MIN_MS;
    let timer: number | undefined;
    let closed = false;

    const connect = () => {
      if (closed) {
        return;
      }
      report("connecting");
      socket = openSocket();

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
  }, [report]);

  return connection;
}

function openSocket(): WebSocket {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  return new WebSocket(`${protocol}://${window.location.host}/ws`);
}
