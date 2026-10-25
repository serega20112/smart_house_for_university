import "./card.css";
/**
 * Карточка: рамка, которой интерфейс обводит кусок смысла.
 *
 * У карточки нет права на собственное содержимое: она даёт ритм — заголовок, подпись,
 * место для действия и поле. Всё, что внутри, рисует тот, кто карточку попросил.
 */

import type { ReactNode } from "react";

interface CardProps {
  title?: string;
  hint?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

/**
 * Оборачивает содержимое в рамку с шапкой.
 *
 * @param props.title Заголовок карточки.
 * @param props.hint Подпись под заголовком: чем эта карточка занята.
 * @param props.actions Кнопки шапки, если они есть.
 * @param props.children Собственно содержимое.
 * @param props.className Класс, которым срез добавляет свою форму.
 * @returns Разметка карточки.
 */
export function Card({ title, hint, actions, children, className = "" }: CardProps) {
  return (
    <section className={`card ${className}`.trim()}>
      {title ? (
        <header className="card__head">
          <div className="card__heading">
            <h2 className="card__title">{title}</h2>
            {hint ? <p className="card__hint">{hint}</p> : null}
          </div>
          {actions ? <div className="card__actions">{actions}</div> : null}
        </header>
      ) : null}
      <div className="card__body">{children}</div>
    </section>
  );
}
