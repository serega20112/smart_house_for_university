import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

/**
 * Сборка интерфейса.
 *
 * Алиас `@` совпадает с проверкой границ FSD: импорт через него читается как имя слоя,
 * а не как лесенка из `../`. Прокси нужен только для `npm run dev`: прод раздаёт
 * интерфейс сам бэкенд, и там оба пути приходят из одного источника.
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    target: "es2022",
  },
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/ws": { target: "ws://127.0.0.1:8000", ws: true },
    },
  },
});
