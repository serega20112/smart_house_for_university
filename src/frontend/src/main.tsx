/** Application entry point. */

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
 * Shows the sign in screen until the session is known.
 *
 * Rendering the routes before the session is resolved would fire requests
 * without a token, so the gate is deliberately part of the tree.
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
