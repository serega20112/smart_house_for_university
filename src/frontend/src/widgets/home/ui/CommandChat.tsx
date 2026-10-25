import "./chat.css";
/**
 * Панель, где дому говорят фразу словами.
 *
 * Разбор фразы живёт на сервере; экран только отправляет то, что напечатал человек, и
 * показывает, что из этого вышло. Ответ приходит одним текстом — второй раз объяснять
 * теми же словами интерфейс не должен.
 */

import { useEffect, useRef, useState, type KeyboardEvent } from "react";

import * as api from "@/shared/api/client";
import { notify } from "@/shared/lib/notify";

/** Сервер отвечает этим кодом, когда фразу удалось прочитать, но не удалось разобрать. */
const NOT_UNDERSTOOD = 422;

/** Одна реплика в журнале. */
interface Line {
  id: number;
  role: "user" | "answer" | "bad";
  text: string;
}

/** Счётчик реплик: порядок важнее содержимого, поэтому id просто следующий. */
let nextId = 0;

/**
 * Возвращает журнал команд: поле ввода и историю ответов этого посещения.
 *
 * @param props.title Заголовок панели.
 * @param props.onChanged Вызывается, когда команда могла что-то изменить в доме.
 * @returns Разметка панели команд.
 */
export function CommandChat({ title, onChanged }: { title: string; onChanged: () => void }) {
  const [lines, setLines] = useState<Line[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);

  // Новый ответ должен быть виден сразу: журнал прокручиваем к последней строке.
  useEffect(() => {
    const log = logRef.current;
    if (log) {
      log.scrollTop = log.scrollHeight;
    }
  }, [lines]);

  /**
   * Отправляет фразу и записывает, что ответило приложение.
   */
  async function submit(): Promise<void> {
    const phrase = text.trim();
    if (phrase.length === 0 || busy) {
      return;
    }
    setBusy(true);
    setText("");
    setLines((current) => [...current, { id: nextId++, role: "user", text: phrase }]);
    try {
      const result = await api.sendCommand(phrase);
      setLines((current) => [...current, { id: nextId++, role: "answer", text: result.answer }]);
      onChanged();
    } catch (exc) {
      // Отказ разбора — это ответ дома, а не авария: он встает той же репликой.
      const rejected = exc instanceof api.ApiError;
      const reason = rejected ? exc.message : "Команда не выполнена";
      const unheard = rejected && exc.status === NOT_UNDERSTOOD;
      setLines((current) => [
        ...current,
        { id: nextId++, role: unheard ? "answer" : "bad", text: unheard ? `${reason} Попробуйте другими словами.` : reason },
      ]);
      if (!unheard) {
        notify(reason, "bad");
      }
    } finally {
      setBusy(false);
    }
  }

  /**
   * Отправляет по Enter; с Shift оставляет перенос.
   *
   * @param event Событие клавиатуры в поле.
   */
  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>): void {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submit();
    }
  }

  return (
    <section className="chat" aria-label={title}>
      <header className="chat__head">
        <h2 className="chat__title">{title}</h2>
        <p className="chat__hint">Устройство называйте как в списке: «включи Лампа»</p>
      </header>

      <div className="chat__log" ref={logRef}>
        {lines.length === 0 ? (
          <p className="chat__empty">Команд пока не было.</p>
        ) : (
          lines.map((line) => (
            <p key={line.id} className={`bubble bubble--${line.role}`}>
              {line.text}
            </p>
          ))
        )}
      </div>

      <div className="chat__form">
        <textarea
          className="chat__input field__input"
          value={text}
          rows={1}
          placeholder="Скажите дому, что сделать"
          disabled={busy}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={onKeyDown}
        />
        <button className="button button--primary" type="button" disabled={busy || text.trim().length === 0} onClick={() => void submit()}>
          {busy ? "Разбираю…" : "Выполнить"}
        </button>
      </div>
    </section>
  );
}
