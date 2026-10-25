import "./auth.css";
/**
 * Экран, который виден гостю без сессии.
 *
 * Левая панель называет, что аккаунт хранит, — без обещаний и слоганов: человек решает
 * войти или заводиться по факту, а не по рекламе. Правая панель ничего не объясняет и
 * только собирает учётные данные.
 */

import { useState, type FormEvent } from "react";

import { useSession } from "@/entities/session";
import * as api from "@/shared/api/client";
import type { Session } from "@/shared/api/types";

/** Режим экрана: вход или создание аккаунта. */
type Mode = "login" | "register";

/** Что аккаунт держит на сервере — перечень, а не обещание. */
const HELD = ["устройства и их каналы", "платы и их сеть", "цели автоматики", "раскладка экрана"];

/** Минимальная длина пароля, которую принимает бэкенд. */
const PASSWORD_MIN_LENGTH = 8;

/**
 * Собирает учётные данные аккаунта и заводит сессию.
 *
 * Регистрация и вход делят одну форму, потому что поля нужны те же, а гость не должен
 * угадывать, какая кнопка к какому пути относится.
 */
export function AuthPage() {
  const { signIn } = useSession();
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const signing = mode === "login";

  /**
   * Отправляет форму: вход для старого аккаунта, создание для нового.
   *
   * @param event Событие отправки формы.
   */
  async function submit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const session: Session = signing
        ? await api.login({ email, password })
        : await api.register({
            email,
            password,
            display_name: displayName.trim() || email.split("@")[0],
          });
      signIn(session);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Не удалось войти");
      setBusy(false);
    }
  }

  return (
    <div className="auth">
      <section className="auth__aside">
        <div className="auth__brand">
          <span className="auth__mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 10.5 12 4l8 6.5" />
              <path d="M6 9.5V19h12V9.5" />
              <path d="M10 19v-4.5h4V19" />
            </svg>
          </span>
          <h1 className="auth__brand-name">Умный дом</h1>
        </div>

        <p className="auth__lead">Аккаунт держит на сервере:</p>
        <ul className="auth__list">
          {HELD.map((item) => (
            <li key={item} className="auth__line">
              {item}
            </li>
          ))}
        </ul>

        <p className="auth__foot">
          Данные читаются с вашей платы; никуда дальше сервера они не уходят.
        </p>
      </section>

      <form className="auth__panel" onSubmit={(event) => void submit(event)}>
        <h2 className="auth__title">{signing ? "Вход" : "Новый аккаунт"}</h2>

        {!signing ? (
          <label className="field">
            <span className="field__label">Имя на экране</span>
            <input
              className="field__input"
              value={displayName}
              maxLength={80}
              placeholder="Как к вам обращаться"
              autoComplete="nickname"
              onChange={(event) => setDisplayName(event.target.value)}
            />
          </label>
        ) : null}

        <label className="field">
          <span className="field__label">Почта</span>
          <input
            className="field__input"
            type="email"
            value={email}
            placeholder="you@example.com"
            autoComplete="username"
            required
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>

        <label className="field">
          <span className="field__label">Пароль</span>
          <input
            className="field__input"
            type="password"
            value={password}
            minLength={signing ? undefined : PASSWORD_MIN_LENGTH}
            placeholder={signing ? "" : `Не короче ${PASSWORD_MIN_LENGTH} символов`}
            autoComplete={signing ? "current-password" : "new-password"}
            required
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>

        {error ? <p className="notice notice--bad">{error}</p> : null}

        <button className="button button--primary" type="submit" disabled={busy}>
          {busy ? "Проверяю…" : signing ? "Войти" : "Создать аккаунт"}
        </button>

        <button
          className="auth__switch"
          type="button"
          onClick={() => {
            setError(null);
            setMode(signing ? "register" : "login");
          }}
        >
          {signing ? "Аккаунта ещё нет — создать" : "Аккаунт уже есть — войти"}
        </button>
      </form>
    </div>
  );
}
