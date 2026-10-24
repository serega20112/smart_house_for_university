/**
 * Чат свободных команд, опирающийся на понимание обычного текста.
 *
 * Экран отправляет предложение целиком и показывает то, что ответило приложение:
 * разбором слов занимается бэкенд, и подсказок про «похожие команды» здесь нет.
 */

import { useState } from "react";

import * as api from "../../services/api";

interface ChatMessage {
  id: number;
  role: "user" | "system";
  text: string;
}

const SUGGESTIONS = [
  "включи свет",
  "выключи всё",
  "сделай прохладнее",
  "какая температура?",
  "через полчаса сделай 20 градусов",
];

interface CommandChatProps {
  title?: string;
}

/**
 * Собирает написанное, отправляет одним запросом и ведёт переписку.
 *
 * @param props.title Личный заголовок виджета.
 */
export function CommandChat({ title }: CommandChatProps) {
  const [text, setText] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([
    { id: 0, role: "system", text: "Напишите команду своими словами." },
  ]);

  async function submit(command: string): Promise<void> {
    const trimmed = command.trim();
    if (!trimmed) {
      return;
    }
    setText("");
    setMessages((current) => [
      ...current,
      { id: current.length, role: "user", text: trimmed },
    ]);
    try {
      const result = await api.sendCommand(trimmed);
      setMessages((current) => [
        ...current,
        { id: current.length, role: "system", text: result.answer },
      ]);
    } catch (exc) {
      const reason = exc instanceof Error ? exc.message : "Не удалось выполнить команду";
      setMessages((current) => [...current, { id: current.length, role: "system", text: reason }]);
    }
  }

  return (
    <section className="chat">
      <header className="chat__head">
        <h2 className="chat__title">{title ?? "Команды"}</h2>
        <p className="chat__hint">Понимает свободные формулировки</p>
      </header>
      <div className="chat__log">
        {messages.map((message) => (
          <p
            key={message.id}
            className={`bubble bubble--${message.role}`.trim()}
          >
            {message.text}
          </p>
        ))}
      </div>
      <div className="chat__suggestions">
        {SUGGESTIONS.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            className="chip"
            onClick={() => void submit(suggestion)}
          >
            {suggestion}
          </button>
        ))}
      </div>
      <form
        className="chat__form"
        onSubmit={(event) => {
          event.preventDefault();
          void submit(text);
        }}
      >
        <input
          className="chat__input"
          value={text}
          placeholder="Например: сделай в комнате прохладнее"
          onChange={(event) => setText(event.target.value)}
        />
        <button className="button button--primary" type="submit">
          Отправить
        </button>
      </form>
    </section>
  );
}
