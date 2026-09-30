/** Application entry point. */

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { Layout } from "./components/Layout";
import { AutomationPage } from "./pages/AutomationPage";
import { DevicesPage } from "./pages/DevicesPage";
import { HomePage } from "./pages/HomePage";
import { ScenariosPage } from "./pages/ScenariosPage";
import "./styles/app.css";

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: <HomePage /> },
      { path: "/devices", element: <DevicesPage /> },
      { path: "/automation", element: <AutomationPage /> },
      { path: "/scenarios", element: <ScenariosPage /> },
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
