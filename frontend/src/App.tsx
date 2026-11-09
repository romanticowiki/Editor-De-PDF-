import { useEffect } from "react";

import { ToolsMenu } from "./components/catalog/ToolsMenu";
import { AppShell } from "./components/layout/AppShell";
import { ThemeToggle } from "./components/ui/ThemeToggle";
import { useApiHealth } from "./hooks/useApiHealth";
import { useEngineAvailability } from "./hooks/useEngineAvailability";
import { useHashRoute } from "./hooks/useHashRoute";
import { usePreventWindowFileDrop } from "./hooks/usePreventWindowFileDrop";
import { HomePage } from "./pages/HomePage";
import { ToolPage } from "./pages/ToolPage";
import { findToolBySlug } from "./tools/catalog";

export function App() {
  usePreventWindowFileDrop();
  const apiHealth = useApiHealth();
  const engines = useEngineAvailability(apiHealth);
  const path = useHashRoute();
  const tool = findToolBySlug(path.slice(1));

  useEffect(() => {
    // Al cambiar de página: arriba del todo y foco en el contenido (lectores de pantalla).
    window.scrollTo({ top: 0 });
    document.getElementById("contenido")?.focus({ preventScroll: true });
  }, [path]);

  return (
    <AppShell
      center={tool ? <ToolsMenu engines={engines} /> : null}
      end={<ThemeToggle />}
    >
      {tool ? (
        // `key`: cambiar de herramienta empieza de cero (archivo, opciones y peticiones).
        <ToolPage key={tool.id} tool={tool} apiHealth={apiHealth} engines={engines} />
      ) : (
        <HomePage engines={engines} />
      )}
    </AppShell>
  );
}
