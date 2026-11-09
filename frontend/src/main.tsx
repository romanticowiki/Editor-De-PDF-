import "@fontsource-variable/manrope";
import "./index.css";

import { MotionConfig } from "motion/react";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { ToastProvider } from "./components/toast/ToastProvider";
import { applyTheme, readThemePreference } from "./hooks/useTheme";

// Antes del primer render: evita un destello con el tema equivocado.
applyTheme(readThemePreference());

const rootElement = document.getElementById("root");
if (!rootElement) throw new Error("No se encontró #root en index.html.");

createRoot(rootElement).render(
  <StrictMode>
    {/* Respeta "reducir movimiento" del sistema en todas las animaciones. */}
    <MotionConfig reducedMotion="user">
      <ToastProvider>
        <App />
      </ToastProvider>
    </MotionConfig>
  </StrictMode>,
);
