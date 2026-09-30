/** Page shell with the navigation between the three screens. */

import { NavLink, Outlet } from "react-router-dom";

const LINKS = [
  { to: "/", label: "Главная", end: true },
  { to: "/devices", label: "Устройства", end: false },
  { to: "/automation", label: "Автоматизация", end: false },
  { to: "/scenarios", label: "Сценарии", end: false },
];

export function Layout() {
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
        <p className="sidebar__note">ESP8266 · 6 реле · DHT22</p>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
