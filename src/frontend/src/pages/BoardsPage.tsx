/**
 * Экран плат текущего аккаунта.
 *
 * Плату не настраивают в прошивке: при первом запуске она вырабатывает собственный
 * ключ и просит хозяина. Человек держит плату в руках, зажимает кнопку FLASH при
 * подаче питания и нажимает одну кнопку здесь. В код не записано ни одного секрета,
 * поэтому один и тот же бинарник получают все.
 *
 * Сеть плате тоже сообщают здесь: она хранит её в своей памяти, а сервер передаёт
 * значения по уже открытому сокету. Плата, которую ни разу не настраивали, поднимает
 * собственную точку доступа и настраивается на той странице, что она сама отдаёт.
 */

import { useCallback, useEffect, useState } from "react";

import { Badge } from "../components/Badge";
import { Card } from "../components/Card";
import { BoardNetworkEditor } from "../features/boards/BoardNetworkEditor";
import { useRealtime } from "../services/realtime";
import * as api from "../services/api";
import type { Board, BoardClaim } from "../services/types";

/** Как часто перечитывать список плат, которые ищут хозяина, пока экран открыт. */
const POLL_MS = 5000;

export function BoardsPage() {
  const [boards, setBoards] = useState<Board[]>([]);
  const [claims, setClaims] = useState<BoardClaim[]>([]);
  const [names, setNames] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const loadBoards = useCallback(async () => {
    try {
      setBoards(await api.fetchBoards());
      setError(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Не удалось получить список плат");
    }
  }, []);

  const loadClaims = useCallback(async () => {
    try {
      const waiting = await api.fetchBoardClaims();
      setClaims(waiting);
      setNames((current) => {
        const next = { ...current };
        for (const claim of waiting) {
          next[claim.claim_token] ??= `ESP ${claim.label}`;
        }
        return next;
      });
    } catch {
      // A failed poll is not worth a notice: the next one will probably work.
    }
  }, []);

  useEffect(() => {
    void loadBoards();
    void loadClaims();
    const timer = setInterval(() => void loadClaims(), POLL_MS);
    return () => clearInterval(timer);
  }, [loadBoards, loadClaims]);

  useRealtime({
    enabled: true,
    onMessage: (message) => {
      if (message.type === "board.announcement_published" || message.type === "board.online") {
        void loadClaims();
        void loadBoards();
      }
    },
  });

  /**
   * Забирает объявленную плату за текущим аккаунтом.
   *
   * @param token Токен предложения.
   * @returns Ничего: списки перечитываются после ответа сервера.
   */
  async function takeBoard(token: string): Promise<void> {
    const name = (names[token] ?? "").trim();
    if (!name) {
      return;
    }
    try {
      await api.claimBoard({ claim_token: token, name });
      await loadClaims();
      await loadBoards();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Не удалось забрать плату");
    }
  }

  /**
   * Убирает плату из аккаунта.
   *
   * @param boardId Идентификатор платы.
   * @returns Ничего: список перечитывается после ответа сервера.
   */
  async function unpair(boardId: string): Promise<void> {
    try {
      await api.revokeBoard(boardId);
      await loadBoards();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Не удалось отвязать плату");
    }
  }

  return (
    <div className="page">
      <header className="page__head">
        <div>
          <h1 className="page__title">Платы</h1>
          <p className="page__subtitle">ESP8266, подключённые к вашему аккаунту</p>
        </div>
      </header>

      {error ? <p className="notice notice--bad">{error}</p> : null}

      <Card
        title="Найденные платы"
        hint="Плата просит владельца, пока её держат в руках"
      >
        {claims.length === 0 ? (
          <p className="empty">
            Никто не ищет владельца. Включите плату, зажмите кнопку FLASH и не
            отпускайте пару секунд — она мигнёт реле.
          </p>
        ) : (
          <ul className="list">
            {claims.map((claim) => (
              <li key={claim.claim_token} className="list__item">
                <div>
                  <span className="list__title">ESP {claim.label}</span>
                  <span className="list__note">
                    до {new Date(claim.expires_at).toLocaleTimeString()}
                  </span>
                </div>
                <div className="sysbar">
                  <input
                    className="chat__input"
                    value={names[claim.claim_token] ?? ""}
                    placeholder="Название"
                    onChange={(event) =>
                      setNames((current) => ({
                        ...current,
                        [claim.claim_token]: event.target.value,
                      }))
                    }
                  />
                  <button
                    type="button"
                    className="button button--primary"
                    onClick={() => void takeBoard(claim.claim_token)}
                  >
                    Забрать
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Подключённые платы" hint={`Всего: ${boards.length}`}>
        {boards.length === 0 ? (
          <p className="empty">Плат пока нет</p>
        ) : (
          <ul className="list">
            {boards.map((board) => (
              <li key={board.id} className="list__item">
                <div>
                  <span className="list__title">{board.name}</span>
                  <span className="list__note">
                    {board.last_seen_at
                      ? `последняя связь ${new Date(board.last_seen_at).toLocaleString()}`
                      : "ещё не подключалась"}
                  </span>
                </div>
                <div className="sysbar">
                  <Badge
                    tone={board.online ? "ok" : "bad"}
                    label={board.online ? "ONLINE" : "OFFLINE"}
                  />
                  <button
                    type="button"
                    className="button button--ghost"
                    onClick={() => void unpair(board.id)}
                  >
                    Отвязать
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {boards.length > 0 ? (
        <Card
          title="Сеть плат"
          hint="Плата хранит эти данные в своей памяти и подключается к указанной сети"
        >
          <div className="grid grid--editors">
            {boards.map((board) => (
              <BoardNetworkEditor
                key={board.id}
                board={board}
                onSaved={() => void loadBoards()}
                onError={setError}
              />
            ))}
          </div>
        </Card>
      ) : null}
    </div>
  );
}