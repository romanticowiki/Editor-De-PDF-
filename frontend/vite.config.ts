/// <reference types="vitest/config" />
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv, type Plugin } from "vite";

import { DEFAULT_API_BASE_URL } from "./src/config/defaults.ts";

const HOST = "127.0.0.1";
// Debe coincidir con `cors_origins` del backend.
const PORT = 5173;

/** CSP estricta solo en build: en desarrollo Vite necesita scripts inline para HMR. */
function contentSecurityPolicy(apiOrigin: string): Plugin {
  const policy = [
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'", // Motion anima mediante atributos style
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    `connect-src 'self' ${apiOrigin}`.trim(),
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'none'",
  ].join("; ");

  return {
    name: "pdfeditor:csp",
    apply: "build",
    transformIndexHtml: () => [
      { tag: "meta", attrs: { "http-equiv": "Content-Security-Policy", content: policy }, injectTo: "head-prepend" },
    ],
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "VITE_");
  const apiBase = env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL;
  // Una base relativa («/api/v1») significa mismo origen: no añade nada a connect-src.
  const apiOrigin = apiBase.startsWith("/") ? "" : new URL(apiBase).origin;

  return {
    // Rutas relativas: el HTML/JS carga igual servido desde «/» (FastAPI, Docker) o empaquetado.
    base: "./",
    plugins: [react(), tailwindcss(), contentSecurityPolicy(apiOrigin)],
    server: { host: HOST, port: PORT, strictPort: true },
    preview: { host: HOST, port: PORT, strictPort: true },
    test: { environment: "node", include: ["src/**/*.test.ts"] },
  };
});
