/** Screen shown to a visitor without a session. */

import { useState, type FormEvent } from "react";

import { useSession } from "../features/auth/SessionProvider";
import * as api from "../services/api";
import type { Session } from "../services/types";

type Mode = "login" | "register";

/**
 * Collects the credentials of the account and starts a session.
 *
 * Registration and login share one form because they need the same fields, and
 * a visitor should not have to guess which button belongs to which flow.
 */
export function AuthPage() {
  const { signIn } = useSession();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const session: Session =
        mode === "login"
          ? await api.login({ email, password })
          : await api.register({
              email,
              password,
              display_name: displayName || email.split("@")[0],
            });
      signIn(session);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Не удалось выполнить вход");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth">
      <form className="auth__card" onSubmit={(event) => void submit(event)}>
        <h1 className="auth__title">Умный дом</h1>
        <p className="auth__hint">
          {mode === "login"
            ? "Войдите, чтобы увидеть своё устройство"
            : "Создайте аккаунт и получите свой набор устройств"}
        </p>

        {mode === "register" ? (
          <label className="field">
            <span className="field__label">Имя</span>
            <input
              className="field__input"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              placeholder="Как к вам обращаться"
            />
          </label>
        ) : null}

        <label className="field">
          <span className="field__label">Email</span>
          <input
            className="field__input"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
            required
          />
        </label>

        <label className="field">
          <span className="field__label">Пароль</span>
          <input
            className="field__input"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Не короче 8 символов"
            required
          />
        </label>

        {error ? <p className="notice notice--bad">{error}</p> : null}

        <button className="button button--primary" type="submit" disabled={busy}>
          {mode === "login" ? "Войти" : "Зарегистрироваться"}
        </button>

        <button
          className="button button--ghost"
          type="button"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
        >
          {mode === "login" ? "Нет аккаунта? Зарегистрироваться" : "Уже есть аккаунт? Войти"}
        </button>
      </form>
    </div>
  );
}
