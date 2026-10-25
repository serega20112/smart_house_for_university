/**
 * Точка входа приложения.
 *
 * Слой app только собирает всё вместе: порядок провайдеров, таблицу маршрутов и охрану
 * входа. Маршруты рисуются лишь после того, как сессия разрешена, — иначе экраны ушли бы
 * запросами без токена.
 */

import { StrictMode, useEffect } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { SessionProvider, useSession } from "@/entities/session";
import { AppShell } from "@/widgets/layout";
import { AuthPage } from "@/pages/auth";
import { AutomationPage } from "@/pages/automation";
import { BoardsPage } from "@/pages/boards";
import { DevicesPage } from "@/pages/devices";
import { HomePage } from "@/pages/home";
import { ScenariosPage } from "@/pages/scenarios";
import { applyTheme, rememberedTheme, rememberTheme } from "@/shared/lib/theme";

// Порядок глобальных таблиц важен: константы → сброс → каркас → контролы → паттерны → движение.
import "@/app/styles/tokens.css";
import "@/app/styles/base.css";
import "@/app/styles/layout.css";
import "@/app/styles/controls.css";
import "@/app/styles/patterns.css";
import "@/app/styles/motion.css";
// У всплывающих подтверждений нет компонента-владельца, поэтому база у них общая.
import "@/app/styles/toasts.css";

/**
 * Красит дом в тему аккаунта и решает, что показать: вход или маршруты.
 *
 * Первый кадр не может ждать ответа `/preferences`: пока настройки в пути, берётся тема,
 * которую помнит браузер.
 */
function Gate(): JSX.Element {
  const { profile, preferences, ready } = useSession();

  useEffect(() => {
    if (!preferences) {
      applyTheme(rememberedTheme());
      return;
    }
    applyTheme(preferences.theme);
    rememberTheme(preferences.theme);
  }, [preferences]);

  if (!ready) {
    return (
      <div className="boot">
        <span className="boot__dot" />
        <span>Проверяю сессию…</span>
      </div>
    );
  }

  return profile ? <RouterProvider router={router} /> : <AuthPage />;
}

const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { path: "/", element: <HomePage /> },
      { path: "/devices", element: <DevicesPage /> },
      { path: "/boards", element: <BoardsPage /> },
      { path: "/automation", element: <AutomationPage /> },
      { path: "/scenarios", element: <ScenariosPage /> },
    ],
  },
]);

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <SessionProvider>
      <Gate />
    </SessionProvider>
  </StrictMode>,
);
