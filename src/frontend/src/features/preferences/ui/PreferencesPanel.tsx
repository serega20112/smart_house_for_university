import "./preferences.css";
/**
 * Профиль аккаунта: кто вошёл и как ему удобнее смотреть на дом.
 *
 * Отдельного раздела под это нет — и не нужно. Тему, единицы и панель команд выбирают
 * один раз за жизнь аккаунта, поэтому они живут в панели, которую открывает знак
 * аккаунта в боковой панели: настройки — не ещё одна комната дома, а способ с ним
 * обращаться.
 */

import { useEffect, useRef } from "react";

import { usePreferences } from "../model/use-preferences";
import { useSession } from "@/entities/session";
import { firstNameOf, initialsOf } from "@/shared/lib/display";
import { formatDay } from "@/shared/lib/format";
import { applyTheme, rememberTheme, type ThemeName } from "@/shared/lib/theme";
import type { TemperatureUnit } from "@/shared/api/types";
import { Toggle } from "@/shared/ui";

/** Знаки панели: рисованы кодом, чтобы краситься состоянием, а не картинкой. */
const ICONS: Record<string, JSX.Element> = {
  sun: (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </>
  ),
  moon: <path d="M20 14.5A8.5 8.5 0 1 1 9.5 4 7 7 0 0 0 20 14.5Z" />,
  close: <path d="M6 6l12 12M18 6L6 18" />,
  logout: (
    <>
      <path d="M14 5H7a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h7" />
      <path d="M17 8l4 4-4 4M21 12H11" />
    </>
  ),
};

const THEMES: readonly { name: ThemeName; label: string; icon: string }[] = [
  { name: "dark", label: "Тёмная", icon: "moon" },
  { name: "light", label: "Светлая", icon: "sun" },
];

const UNITS: readonly { name: TemperatureUnit; label: string }[] = [
  { name: "C", label: "°C" },
  { name: "F", label: "°F" },
];

interface PreferencesPanelProps {
  open: boolean;
  onClose: () => void;
}

/**
 * Показывает профиль и настройки вошедшего аккаунта.
 *
 * Панель затемняет дом целиком, поэтому появляется только по просьбе и уходит по Esc,
 * клику мимо карточки или кнопке закрытия.
 *
 * @param props.open Открыта ли панель сейчас.
 * @param props.onClose Вызывается, когда человек кончил с ней.
 */
export function PreferencesPanel({ open, onClose }: PreferencesPanelProps) {
  const { profile, signOut } = useSession();
  const { unit, theme, showCommandChat, busy, changeUnit, changeTheme, toggleCommandChat } =
    usePreferences();
  const cardRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    const onKey = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    cardRef.current?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open || !profile) {
    return null;
  }

  /**
   * Меняет тему и локально, и на сервере.
   *
   * Локальная копия нужна, чтобы следующий вход в дом был того же цвета до того, как
   * настройки доедут с сервера.
   *
   * @param next Тема, которую выбрал человек.
   */
  function chooseTheme(next: ThemeName): void {
    applyTheme(next);
    rememberTheme(next);
    changeTheme(next);
  }

  return (
    <div className="sheet" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <div
        className="sheet__card"
        role="dialog"
        aria-modal="true"
        aria-label="Профиль и настройки"
        tabIndex={-1}
        ref={cardRef}
      >
        <header className="sheet__head">
          <span className="sheet__avatar" aria-hidden="true">
            {initialsOf(profile.display_name || profile.email) ?? "?"}
          </span>
          <div className="sheet__who">
            <p className="sheet__name">{firstNameOf(profile.display_name)}</p>
            <p className="sheet__email">{profile.email}</p>
          </div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Закрыть панель">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" aria-hidden="true">
              {ICONS.close}
            </svg>
          </button>
        </header>

        <div className="sheet__body">
          <div className="sheet__row">
            <div className="switch-row">
              <span className="switch-row__text">
                <span className="switch-row__title">Тема</span>
                <span className="switch-row__note">Выбор сохраняется за аккаунтом</span>
              </span>
            </div>
            <div className="segmented" role="group" aria-label="Тема интерфейса">
              {THEMES.map((option) => (
                <button
                  key={option.name}
                  type="button"
                  disabled={busy}
                  aria-pressed={option.name === theme}
                  className={`segmented__option ${option.name === theme ? "segmented__option--on" : ""}`.trim()}
                  onClick={() => option.name !== theme && chooseTheme(option.name)}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    {ICONS[option.icon]}
                  </svg>
                  <span>{option.label}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="sheet__row">
            <div className="switch-row">
              <span className="switch-row__text">
                <span className="switch-row__title">Температура</span>
                <span className="switch-row__note">Единицы для климата и целей</span>
              </span>
            </div>
            <div className="segmented" role="group" aria-label="Единицы температуры">
              {UNITS.map((option) => (
                <button
                  key={option.name}
                  type="button"
                  disabled={busy}
                  aria-pressed={option.name === unit}
                  className={`segmented__option ${option.name === unit ? "segmented__option--on" : ""}`.trim()}
                  onClick={() => option.name !== unit && void changeUnit(option.name)}
                >
                  <span>{option.label}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="sheet__row">
            <div className="switch-row">
              <span className="switch-row__text">
                <span className="switch-row__title">Панель команд</span>
                <span className="switch-row__note">Поле команд на главном экране</span>
              </span>
            </div>
            <Toggle
              checked={showCommandChat}
              disabled={busy}
              label="Панель команд на главном экране"
              onChange={(next) => void toggleCommandChat(next)}
            />
          </div>

          <dl className="facts">
            <div className="facts__row">
              <dt>Аккаунт создан</dt>
              <dd>{formatDay(profile.created_at)}</dd>
            </div>
            <div className="facts__row">
              <dt>Имя на экране</dt>
              <dd>{profile.display_name}</dd>
            </div>
          </dl>
        </div>

        <footer className="sheet__foot">
          <button type="button" className="button sheet__quit" onClick={signOut} disabled={busy}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              {ICONS.logout}
            </svg>
            <span>Выйти из аккаунта</span>
          </button>
        </footer>
      </div>
    </div>
  );
}
