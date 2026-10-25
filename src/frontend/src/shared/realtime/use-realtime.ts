/**
 * Поток событий дома.
 *
 * Соединение открывается под одноразовым билетом: токен сессии в адресе сокета не
 * ездит. Когда связь рвётся, хук ждёт с нарастающей паузой и просит новый билет —
 * старый сервер уже обменял и второй раз не примет.
 *
 * Владелец соединения — экран, который подписан на изменения; он говорит, что делать с
 * очередным фактом, а хук следит, чтобы факты доходили.
 */

import { useEffect, useRef, useState } from "react";

import { fetchRealtimeTicket } from "@/shared/api/client";
import { getToken, onSessionChange } from "@/shared/lib/token";
import type { RealtimeEvent } from "@/shared/api/types";

/** Состояние соединения, которое показывают человеку. */
export type ConnectionState = "connecting" | "open" | "closed";

/** Русская подпись состояния соединения: код наружу не показывают. */
export const CONNECTION_LABELS: Record<ConnectionState, string> = {
  connecting: "подключаюсь",
  open: "на связи",
  closed: "переподключение",
};

/** Первый шаг паузы между попытками пересоединиться. */
const FIRST_RETRY_MS = 1200;

/** Потолок паузы: дальше ждать чаще уже не имеет смысла. */
const MAX_RETRY_MS = 15_000;

/** Что делает подписчик, когда приходит событие. */
export type EventHandler = (event: RealtimeEvent, payload: Record<string, unknown>) => void;

/**
 * Возвращает адрес сокета этого же сервера.
 *
 * @returns Строка `ws://` или `wss://` с путем `/ws`.
 */
function socketUrl(): string {
  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${window.location.host}/ws`;
}

/**
 * Держит открытым соединение с событиями собственного дома.
 *
 * @param handler Функция, которой передаётся каждый факт; её свежее значение берётся
 *   на каждое событие, поэтому подписчику не нужно пересобирать соединение.
 * @returns Состояние соединения для показа на экране.
 */
export function useRealtime(handler: EventHandler): ConnectionState {
  const [connection, setConnection] = useState<ConnectionState>("connecting");
  const handlerRef = useRef(handler);
  handlerRef.current = handler;

  useEffect(() => {
    let socket: WebSocket | null = null;
    let timer: number | null = null;
    let attempt = 0;
    let stopped = false;

    /**
     * Закрывает текущую попытку и, если время пришло, планирует следующую.
     *
     * Отказ сокета приходит и как `error`, и как `close`: без одной очереди браузер
     * поднял бы два соединения подряд.
     */
    const scheduleRetry = (): void => {
      if (stopped) {
        return;
      }
      if (timer !== null) {
        return;
      }
      if (!getToken()) {
        setConnection("closed");
        return;
      }
      setConnection("connecting");
      const delay = Math.min(FIRST_RETRY_MS * 2 ** attempt, MAX_RETRY_MS);
      attempt += 1;
      timer = window.setTimeout(() => {
        timer = null;
        void open();
      }, delay);
    };

    /**
     * Просит билет и поднимает соединение.
     */
    async function open(): Promise<void> {
      if (stopped || !getToken()) {
        return;
      }
      setConnection("connecting");
      try {
        const ticket = await fetchRealtimeTicket();
        if (stopped) {
          return;
        }
        socket = new WebSocket(`${socketUrl()}?ticket=${encodeURIComponent(ticket.ticket)}`);
        socket.addEventListener("open", () => {
          attempt = 0;
          setConnection("open");
        });
        socket.addEventListener("message", (message: MessageEvent<string>) => {
          read(message.data);
        });
        socket.addEventListener("close", scheduleRetry);
        socket.addEventListener("error", scheduleRetry);
      } catch {
        // Билет не получен: сервер отверг сессию или сеть лежит — пробуем позже.
        scheduleRetry();
      }
    }

    /**
     * Разбирает одно сообщение и отдаёт его подписчику.
     *
     * Формат фиксирует концентратор: `type` и `payload`. Всё остальное — молчаливый
     * пропуск: ломать из-за непонятной строки живое соединение не стоит.
     *
     * @param raw Текст сообщения.
     */
    function read(raw: string): void {
      let frame: { type?: string; payload?: unknown };
      try {
        frame = JSON.parse(raw) as { type?: string; payload?: unknown };
      } catch {
        return;
      }
      if (typeof frame.type !== "string") {
        return;
      }
      const payload =
        typeof frame.payload === "object" && frame.payload !== null
          ? (frame.payload as Record<string, unknown>)
          : {};
      handlerRef.current(frame.type as RealtimeEvent, payload);
    }

    /**
     * Разрывает соединение и забывает все отложенные попытки.
     */
    function teardown(): void {
      stopped = true;
      if (timer !== null) {
        window.clearTimeout(timer);
        timer = null;
      }
      if (socket) {
        socket.removeEventListener("close", scheduleRetry);
        socket.removeEventListener("error", scheduleRetry);
        socket.close();
        socket = null;
      }
    }

    void open();
    // Смена сессии — это новый дом: старое соединение с чужим билетом бесполезно.
    const reconnect = onSessionChange(() => {
      teardown();
      // Разорвали прежнее соединение осознанно — следующая попытка начинается заново.
      stopped = false;
      attempt = 0;
      void open();
    });

    return () => {
      reconnect();
      teardown();
    };
  }, []);

  return connection;
}
