import "./board-network.css";
/**
 * Сеть, которую предписано использовать плате.
 *
 * Плата спрашивает сеть один раз, на своей точке доступа, и больше ничего не выдумывает:
 * поэтому экран обязан отдавать ровно те значения, которые прошивка примет. Ограничения
 * взяты из `firmware/src/network_config.h`: имя сети до 32 знаков, пароль до 64, адрес
 * сервера только числовой IPv4, путь до 23 знаков.
 */

import { useState, type FormEvent } from "react";

import * as api from "@/shared/api/client";
import { formatMoment } from "@/shared/lib/format";
import { notify } from "@/shared/lib/notify";
import type { BoardNetwork } from "@/shared/api/types";

/** Ограничения прошивки: длиннее плата просто не примет. */
const SSID_MAX = 32;
const PASSWORD_MAX = 64;
const HOST_MAX = 15;
const PATH_MAX = 23;

/** Значения по умолчанию те же, что в прошивке. */
const DEFAULT_SERVER_PORT = 8000;
const DEFAULT_SOCKET_PORT = 8001;
const DEFAULT_SOCKET_PATH = "/ws/board";

/** Адрес сервера, с которым говорит прошивка: только четыре октета, без имён. */
const IPV4 = /^\d{1,3}(\.\d{1,3}){3}$/;

interface BoardNetworkEditorProps {
  boardId: string;
  boardName: string;
  network: BoardNetwork | null;
  onSaved: () => void;
  onCancel: () => void;
}

/**
 * Возвращает форму предписанной сети платы.
 *
 * @param props.boardId Плата, сеть которой правят.
 * @param props.boardName Её имя — для подписи и подтверждения.
 * @param props.network Раньше сохранённая сеть или None, если платы ещё не задавали сеть.
 * @param props.onSaved Вызывается, когда сервер принял значения.
 * @param props.onCancel Вызывается по кнопке отмены.
 */
export function BoardNetworkEditor({
  boardId,
  boardName,
  network,
  onSaved,
  onCancel,
}: BoardNetworkEditorProps) {
  const [ssid, setSsid] = useState(network?.ssid ?? "");
  const [password, setPassword] = useState("");
  const [host, setHost] = useState(network?.host ?? "");
  const [serverPort, setServerPort] = useState(network?.server_port ?? DEFAULT_SERVER_PORT);
  const [socketPort, setSocketPort] = useState(network?.socket_port ?? DEFAULT_SOCKET_PORT);
  const [socketPath, setSocketPath] = useState(network?.socket_path ?? DEFAULT_SOCKET_PATH);
  const [busy, setBusy] = useState(false);

  /**
   * Проверяет форму до отправки и отправляет, если всё годно.
   *
   * Плата не умеет разбирать имена и длинные строки, поэтому отказ здесь дешевле, чем
   * молчаливо сохранённые настройки, которые железо не примет.
   *
   * @param event Событие отправки формы.
   */
  async function submit(event: FormEvent): Promise<void> {
    event.preventDefault();
    if (ssid.trim().length === 0) {
      notify("Название сети пустое", "bad");
      return;
    }
    if (!IPV4.test(host.trim())) {
      notify("Сервер должен быть числовым адресом IPv4", "bad");
      return;
    }
    setBusy(true);
    try {
      await api.updateBoardNetwork(boardId, {
        ssid: ssid.trim(),
        password,
        host: host.trim(),
        server_port: serverPort,
        socket_port: socketPort,
        socket_path: socketPath.trim(),
      });
      notify(`${boardName}: сеть предписана, плата применит её при следующем звонке`, "ok");
      onSaved();
    } catch (exc) {
      notify(exc instanceof Error ? exc.message : "Сеть не сохранилась", "bad");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="bnet" onSubmit={(event) => void submit(event)}>
      <header className="bnet__head">
        <h3 className="bnet__title">{boardName}</h3>
        <p className="bnet__note">
          {network?.configured
            ? `Сохранено ${network.updated_at ? formatMoment(network.updated_at) : "ранее"}`
            : "Плате ещё не предписана сеть"}
        </p>
      </header>

      <label className="field">
        <span className="field__label">Название сети</span>
        <input
          className="field__input"
          value={ssid}
          maxLength={SSID_MAX}
          placeholder="Имя точки доступа"
          onChange={(event) => setSsid(event.target.value)}
        />
      </label>

      <label className="field">
        <span className="field__label">Пароль сети</span>
        <input
          className="field__input"
          type="password"
          value={password}
          maxLength={PASSWORD_MAX}
          placeholder={network?.configured ? "Оставьте пустым, чтобы не менять" : "Пусто для открытой сети"}
          onChange={(event) => setPassword(event.target.value)}
        />
      </label>

      <label className="field">
        <span className="field__label">Адрес сервера</span>
        <input
          className="field__input"
          value={host}
          maxLength={HOST_MAX}
          placeholder="192.168.0.10"
          inputMode="numeric"
          onChange={(event) => setHost(event.target.value)}
        />
        <span className="bnet__hint">Прошивка разбирает только числовой IPv4</span>
      </label>

      <div className="bnet__pair">
        <label className="field">
          <span className="field__label">Порт сервера</span>
          <input
            className="field__input"
            type="number"
            min={1}
            max={65535}
            value={serverPort}
            onChange={(event) => setServerPort(Number(event.target.value))}
          />
        </label>
        <label className="field">
          <span className="field__label">Порт платы</span>
          <input
            className="field__input"
            type="number"
            min={1}
            max={65535}
            value={socketPort}
            onChange={(event) => setSocketPort(Number(event.target.value))}
          />
        </label>
      </div>

      <label className="field">
        <span className="field__label">Путь сокета платы</span>
        <input
          className="field__input"
          value={socketPath}
          maxLength={PATH_MAX}
          onChange={(event) => setSocketPath(event.target.value)}
        />
      </label>

      <footer className="bnet__foot">
        <button type="button" className="button button--ghost" disabled={busy} onClick={onCancel}>
          Отмена
        </button>
        <button className="button button--primary" type="submit" disabled={busy}>
          {busy ? "Сохраняю…" : "Предписать сеть"}
        </button>
      </footer>
    </form>
  );
}
