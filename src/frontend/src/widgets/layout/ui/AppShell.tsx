import "./app-shell.css";
/**
 * Оболочка страницы с переходом между экранами.
 *
 * Оболочка ничего не знает о доме: она держит навигацию, показывает, кто вошёл, и
 * открывает панель настроек. Иконки рисует код, а не принесённые картинки — так они
 * красятся состоянием и не тянут в сборку ни одного лишнего запроса.
 *
 * Профиль живёт здесь же, в подвале панели: отдельного раздела для него нет, потому что
 * обращения к дому — не ещё один раздел, а способ с ним работать.
 */

import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { PreferencesPanel } from "@/features/preferences";
import { useSession } from "@/entities/session";
import { initialsOf } from "@/shared/lib/display";

/** Знак раздела: маленький штрих, который читается быстрее подписи. */
const ICONS: Record<string, JSX.Element> = {
  home: (
    <>
      <path d="M4 10.5 12 4l8 6.5" />
      <path d="M6 9.5V19h12V9.5" />
      <path d="M10 19v-4.5h4V19" />
    </>
  ),
  devices: (
    <>
      <rect x="4" y="4" width="7" height="7" rx="2" />
      <rect x="13" y="4" width="7" height="7" rx="2" />
      <rect x="4" y="13" width="7" height="7" rx="2" />
      <rect x="13" y="13" width="7" height="7" rx="2" />
    </>
  ),
  boards: (
    <>
      <rect x="5" y="5" width="14" height="14" rx="3" />
      <path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3" />
    </>
  ),
  automation: (
    <>
      <path d="M4 7h10M18 7h2M4 17h2M10 17h10" />
      <circle cx="16" cy="7" r="2" />
      <circle cx="8" cy="17" r="2" />
    </>
  ),
  scenarios: (
    <>
      <circle cx="12" cy="12" r="8" />
      <path d="M12 7.5V12l3 2" />
    </>
  ),
  account: (
    <>
      <circle cx="12" cy="8.2" r="3.6" />
      <path d="M5.2 19.6a7 7 0 0 1 13.6 0" />
    </>
  ),
};

/** Разделы дома: порядок тот же, что и смысл — от обзора к настройке. */
const LINKS = [
  { to: "/", label: "Главная", icon: "home", end: true },
  { to: "/devices", label: "Устройства", icon: "devices", end: false },
  { to: "/boards", label: "Платы", icon: "boards", end: false },
  { to: "/automation", label: "Автоматизация", icon: "automation", end: false },
  { to: "/scenarios", label: "Сценарии", icon: "scenarios", end: false },
];

export function AppShell() {
  const { profile } = useSession();
  const [panelOpen, setPanelOpen] = useState(false);
  const initials = profile ? initialsOf(profile.display_name || profile.email) : null;

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar__brand">
          <span className="sidebar__mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
              {ICONS.home}
            </svg>
          </span>
          <span className="sidebar__name">Умный дом</span>
        </div>

        <nav className="sidebar__nav" aria-label="Разделы">
          {LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                `sidebar__link ${isActive ? "sidebar__link--active" : ""}`.trim()
              }
            >
              <svg
                className="sidebar__icon"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                {ICONS[link.icon]}
              </svg>
              <span>{link.label}</span>
            </NavLink>
          ))}
        </nav>

        <button
          type="button"
          className="sidebar__account"
          onClick={() => setPanelOpen(true)}
          aria-haspopup="dialog"
          aria-expanded={panelOpen}
        >
          <span className="sidebar__avatar" aria-hidden="true">
            {initials ?? "?"}
          </span>
          <span className="sidebar__who">
            <span className="sidebar__user">{profile?.display_name ?? "Гость"}</span>
            <span className="sidebar__note">{profile?.email ?? ""}</span>
          </span>
          <svg
            className="sidebar__account-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            {ICONS.account}
          </svg>
        </button>
      </aside>

      <main className="content">
        <Outlet />
      </main>

      <PreferencesPanel open={panelOpen} onClose={() => setPanelOpen(false)} />
    </div>
  );
}
