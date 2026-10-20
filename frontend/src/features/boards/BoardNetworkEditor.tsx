/**
 * Editor of the network a board is to use.
 *
 * The board keeps the network in its own flash, so nothing here is a setting of
 * the server: the form is a way to tell the board, and the board answers over
 * the socket it already keeps open. A board that is not connected right now
 * cannot be told anything, and the form says so instead of pretending.
 */

import { useEffect, useState } from "react";

import * as api from "../../services/api";
import type { BoardNetwork, EspDevice } from "../../services/types";

interface BoardNetworkEditorProps {
  board: EspDevice;
  onSaved: () => void;
  onError: (message: string) => void;
}

interface Draft {
  ssid: string;
  password: string;
  host: string;
  serverPort: string;
  socketPort: string;
  socketPath: string;
}

const DEFAULTS: Draft = {
  ssid: "",
  password: "",
  host: "",
  serverPort: "8000",
  socketPort: "8765",
  socketPath: "/ws/board",
};

function draftOf(network: BoardNetwork | null): Draft {
  if (!network) {
    return { ...DEFAULTS };
  }
  return {
    ssid: network.ssid,
    password: "",
    host: network.host,
    serverPort: String(network.server_port),
    socketPort: String(network.socket_port),
    socketPath: network.socket_path,
  };
}

export function BoardNetworkEditor({ board, onSaved, onError }: BoardNetworkEditorProps) {
  const [draft, setDraft] = useState<Draft>(() => draftOf(null));
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void api
      .fetchBoardNetwork(board.id)
      .then((network) => {
        if (!cancelled) {
          setDraft(draftOf(network));
        }
      })
      .catch(() => {
        // A board that was never configured has nothing to show, and the empty
        // form is exactly what the person in front of it needs.
      });
    return () => {
      cancelled = true;
    };
  }, [board.id]);

  function patch(next: Partial<Draft>): void {
    setDraft((current) => ({ ...current, ...next }));
  }

  async function save(): Promise<void> {
    const serverPort = Number(draft.serverPort);
    const socketPort = Number(draft.socketPort);
    if (!draft.ssid.trim() || !draft.host.trim()) {
      onError("Укажите имя сети и адрес сервера");
      return;
    }
    if (!Number.isInteger(serverPort) || !Number.isInteger(socketPort)) {
      onError("Порты должны быть числами");
      return;
    }
    setBusy(true);
    try {
      await api.updateBoardNetwork(board.id, {
        ssid: draft.ssid.trim(),
        password: draft.password,
        host: draft.host.trim(),
        server_port: serverPort,
        socket_port: socketPort,
        socket_path: draft.socketPath.trim() || DEFAULTS.socketPath,
      });
      setDraft((current) => ({ ...current, password: "" }));
      onSaved();
    } catch (exc) {
      onError(exc instanceof Error ? exc.message : "Не удалось применить настройки сети");
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="editor">
      <header className="editor__head">
        <h3 className="editor__title">Сеть</h3>
        <span className="editor__dot editor__dot--unavailable" />
      </header>

      {board.current_ssid ? (
        <p className="editor__note">Плата сейчас в сети «{board.current_ssid}»</p>
      ) : (
        <p className="editor__note">Плата не сообщила, в какой сети она работает</p>
      )}

      <label className="field">
        <span>Имя сети</span>
        <input
          value={draft.ssid}
          onChange={(event) => patch({ ssid: event.target.value })}
        />
      </label>

      <label className="field">
        <span>Пароль</span>
        <input
          type="password"
          value={draft.password}
          placeholder="не меняется, если пусто"
          onChange={(event) => patch({ password: event.target.value })}
        />
      </label>

      <label className="field">
        <span>Адрес сервера</span>
        <input
          value={draft.host}
          placeholder="192.168.1.10"
          onChange={(event) => patch({ host: event.target.value })}
        />
      </label>

      <div className="editor__actions">
        <button
          className="button button--primary"
          type="button"
          disabled={busy || !board.online}
          onClick={() => void save()}
        >
          {board.online ? "Применить" : "Плата не на связи"}
        </button>
      </div>
    </article>
  );
}
