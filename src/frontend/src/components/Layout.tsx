/** Page shell with the navigation between the screens. */

import { NavLink, Outlet } from "react-router-dom";

import { useSession } from "../features/auth/SessionProvider";

const LINKS = [
  { to: "/", label: "Главная", end: true },
  { to: "/devices", label: "Устройства", end: false },
  { to: "/boards", label: "Платы", end: false },
  { to: "/automation", label: "Автоматизация", end: false },
  { to: "/scenarios", label: "Сценарии", end: false },
];

export function Layout() {
  const { profile, signOut } = useSession();

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar__brand">
          <span className="sidebar__dot" />
          <span>Умный дом</span>
        </div>
        <nav className="sidebar__nav">
          {LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                `sidebar__link ${isActive ? "sidebar__link--active" : ""}`.trim()
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar__account">
          <span className="sidebar__note">{profile?.email ?? ""}</span>
          <button type="button" className="button button--ghost" onClick={signOut}>
            Выйти
          </button>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
