import "./boards.css";
/**
 * Экран плат.
 *
 * Плата появляется в доме одним способом: дозванивается серверу без хозяина, сервер
 * публикует объявление, и его забирают кнопкой. Ручного сопряжения «введи ключ, который
 * я сам придумал» здесь нет: прошивка генерирует ключ сама и держит его в своей памяти,
 * а значит, человеку этот ключ вводить негде и незачем.
 *
 * Объявления перечитываются по событию потока и раз в пять секунд — на случай, если
 * событие ушло, пока браузер молчал.
 */

import { useCallback, useEffect, useState } from "react";

import { BoardNetworkEditor } from "@/features/board-network";
import * as api from "@/shared/api/client";
import { countNoun, formatAgo, formatIn, formatMoment } from "@/shared/lib/format";
import { boardStatusLabel } from "@/shared/lib/labels";
import { notify } from "@/shared/lib/notify";
import { CONNECTION_LABELS, useRealtime } from "@/shared/realtime/use-realtime";
import type { Board, BoardClaim, BoardNetwork } from "@/shared/api/types";
import { Badge } from "@/shared/ui";

/** Как часто перечитывать предложения платы, если событий потока не дождались. */
const CLAIMS_POLL_MS = 5_000;

/** Имя платы: столько же, сколько принимает домен. */
const BOARD_NAME_MAX = 60;

/** Формы слова «плата» для подписи списка. */
const BOARD_FORMS: [string, string, string] = ["плата", "платы", "плат"];

/** Формы слова «объявление» для очереди предложений. */
const OFFER_FORMS: [string, string, string] = ["объявление", "объявления", "объявлений"];

interface OfferRowProps {
  offer: BoardClaim;
  busy: boolean;
  onClaim: (offer: BoardClaim, name: string) => void;
}

/**
 * Строка одного объявления платы: код, срок и поле с именем.
 *
 * @param props.offer Предложение, которое забирают.
 * @param props.busy Занято ли место другим действием.
 * @param props.onClaim Вызывается с именем, которое человек дал плате.
 */
function OfferRow({ offer, busy, onClaim }: OfferRowProps) {
  const [name, setName] = useState("");

  return (
    <li className="list__item">
      <div className="boards__offer">
        <span className="boards__code num">{offer.label}</span>
        <div>
          <span className="list__title">Плата ждёт хозяина</span>
          <span className="list__note">
            объявилась {formatMoment(offer.announced_at)} · заберут до {formatIn(offer.expires_at)}
          </span>
        </div>
      </div>
      <form
        className="inline-row"
        onSubmit={(event) => {
          event.preventDefault();
          onClaim(offer, name);
        }}
      >
        <input
          className="field__input"
          value={name}
          maxLength={BOARD_NAME_MAX}
          placeholder="Имя платы"
          onChange={(event) => setName(event.target.value)}
        />
        <button className="button button--primary" type="submit" disabled={busy || name.trim().length === 0}>
          Забрать
        </button>
      </form>
    </li>
  );
}

export function BoardsPage() {
  const [boards, setBoards] = useState<Board[]>([]);
  const [claims, setClaims] = useState<BoardClaim[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [networkFor, setNetworkFor] = useState<{ board: Board; network: BoardNetwork | null } | null>(
    null,
  );
  const [busy, setBusy] = useState(false);

  /**
   * Перечитывает платы и предложения одним махом.
   */
  const load = useCallback(async () => {
    try {
      const [list, offers] = await Promise.all([api.fetchBoards(), api.fetchBoardClaims()]);
      setBoards(list);
      setClaims(offers);
      setError(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Платы не прочитались");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // Любое событие про железо меняет или список плат, или очередь предложений.
  const connection = useRealtime(() => void load());

  useEffect(() => {
    const timer = window.setInterval(() => void load(), CLAIMS_POLL_MS);
    return () => window.clearInterval(timer);
  }, [load]);

  /**
   * Забирает объявленную плату за собой.
   *
   * @param offer Предложение, которое забирают.
   * @param name Имя, которое человек дал плате.
   */
  async function claim(offer: BoardClaim, name: string): Promise<void> {
    setBusy(true);
    try {
      await api.claimBoard({ claim_token: offer.claim_token, name: name.trim() });
      notify(`${name.trim()}: плата ваша`, "ok");
      await load();
    } catch (exc) {
      notify(exc instanceof Error ? exc.message : "Плата не забрана", "bad");
    } finally {
      setBusy(false);
    }
  }

  /**
   * Открывает редактор сети платы, предварительно прочитав её текущую сеть.
   *
   * @param board Плата, которой задают сеть.
   */
  async function openNetwork(board: Board): Promise<void> {
    setBusy(true);
    try {
      setNetworkFor({ board, network: await api.fetchBoardNetwork(board.id) });
    } catch (exc) {
      notify(exc instanceof Error ? exc.message : "Сеть платы не прочиталась", "bad");
      setNetworkFor({ board, network: null });
    } finally {
      setBusy(false);
    }
  }

  /**
   * Убирает плату из аккаунта.
   *
   * @param board Плата, которая больше не нужна.
   */
  async function revoke(board: Board): Promise<void> {
    if (!window.confirm(`Убрать «${board.name}»? Устройства на её каналах останутся.`)) {
      return;
    }
    setBusy(true);
    try {
      await api.revokeBoard(board.id);
      notify(`${board.name}: плата убрана`, "ok");
      await load();
    } catch (exc) {
      notify(exc instanceof Error ? exc.message : "Плата не убрана", "bad");
    } finally {
      setBusy(false);
    }
  }

  const online = boards.filter((board) => board.online).length;

  return (
    <div className="page">
      <header className="page__head">
        <div>
          <p className="page__eyebrow">Железо</p>
          <h1 className="page__title">Платы</h1>
          <p className="page__subtitle">
            {boards.length === 0
              ? "Сопряжённых плат нет"
              : `${countNoun(boards.length, BOARD_FORMS)}, ${countNoun(online, BOARD_FORMS)} на связи`}
          </p>
        </div>
      </header>

      {error ? <p className="notice notice--bad">{error}</p> : null}

      <section className="boards__offers" aria-label="Платы без хозяина">
        <header className="boards__section-head">
          <h2 className="boards__section-title">Ждут хозяина</h2>
          <p className="boards__section-note">
            {claims.length === 0 ? "объявлений нет" : `${countNoun(claims.length, OFFER_FORMS)} в очереди`}
          </p>
        </header>

        {claims.length === 0 ? (
          <div className="empty">
            <p className="empty__title">Плата ещё не объявилась</p>
            <p>
              Плата, у которой нет хозяина, звонит серверу сама — как только она
              появится здесь, её можно забрать, назвав своим именем.
            </p>
          </div>
        ) : (
          <ul className="list">
            {claims.map((offer) => (
              <OfferRow
                key={offer.id}
                offer={offer}
                busy={busy}
                onClaim={(item, name) => void claim(item, name)}
              />
            ))}
          </ul>
        )}
      </section>

      <section className="boards__own" aria-label="Мои платы">
        <header className="boards__section-head">
          <h2 className="boards__section-title">Мои платы</h2>
          <p className="boards__section-note">поток событий: {CONNECTION_LABELS[connection]}</p>
        </header>

        {boards.length === 0 ? (
          <div className="empty">
            <p className="empty__title">Сопряжённых плат нет</p>
            <p>Забери объявленную плату выше — она встанет сюда.</p>
          </div>
        ) : (
          <ul className="list">
            {boards.map((board) => (
              <li key={board.id} className="list__item">
                <div className="boards__board">
                  <span className="boards__title">{board.name}</span>
                  <span className="list__note">
                    {board.last_seen_at ? `связь ${formatAgo(board.last_seen_at)}` : "ещё не звонилась"}
                    {board.current_ssid ? ` · в сети ${board.current_ssid}` : ""}
                  </span>
                </div>
                <div className="inline-row">
                  <Badge tone={board.online ? "ok" : "bad"} label={boardStatusLabel(board.online)} />
                  <button type="button" className="button" disabled={busy} onClick={() => void openNetwork(board)}>
                    Сеть
                  </button>
                  <button type="button" className="button button--danger" disabled={busy} onClick={() => void revoke(board)}>
                    Убрать
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}

        {networkFor ? (
          <div className="boards__network">
            <BoardNetworkEditor
              boardId={networkFor.board.id}
              boardName={networkFor.board.name}
              network={networkFor.network}
              onSaved={() => {
                setNetworkFor(null);
                void load();
              }}
              onCancel={() => setNetworkFor(null)}
            />
          </div>
        ) : null}
      </section>
    </div>
  );
}
