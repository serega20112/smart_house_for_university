/** Card container giving the interface its visual rhythm. */

import type { ReactNode } from "react";

interface CardProps {
  title?: string;
  hint?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Card({ title, hint, actions, children, className = "" }: CardProps) {
  return (
    <section className={`card ${className}`.trim()}>
      {title ? (
        <header className="card__head">
          <div>
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
