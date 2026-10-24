/** Точка входа приложения. */

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { Layout } from "./components/Layout";
import { SessionProvider, useSession } from "./features/auth/SessionProvider";
import { AuthPage } from "./pages/AuthPage";
import { AutomationPage } from "./pages/AutomationPage";
import { BoardsPage } from "./pages/BoardsPage";
import { DevicesPage } from "./pages/DevicesPage";
import { HomePage } from "./pages/HomePage";
import { ScenariosPage } from "./pages/ScenariosPage";
import "./styles/app.css";

/**
 * Показывает экран входа, пока сессия неизвестна.
 *
 * Отрисовать маршруты до того, как сессия разрешена, означало бы уйти запросами без
 * токена, поэтому вход нарочно стоит в самом дереве.
 */
function Gate() {
  const { profile, ready } = useSession();
  if (!ready) {
    return <p className="empty">Проверяю сессию…</p>;
  }
  return profile ? <RouterProvider router={router} /> : <AuthPage />;
}

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: <HomePage /> },
      { path: "/devices", element: <DevicesPage /> },
      { path: "/boards", element: <BoardsPage /> },
      { path: "/automation", element: <AutomationPage /> },
      { path: "/scenarios", element: <ScenariosPage /> },
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <SessionProvider>
      <Gate />
    </SessionProvider>
  </StrictMode>,
);
