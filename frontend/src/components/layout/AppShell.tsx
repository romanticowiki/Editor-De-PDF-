import type { ReactNode } from "react";

import { cx } from "../../lib/cx";
import { Brand } from "./Brand";

export const PAGE_CONTAINER = "mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-10";

interface AppShellProps {
  /** Contenido centrado de la cabecera (el menú de herramientas en las páginas internas). */
  center?: ReactNode;
  end: ReactNode;
  children: ReactNode;
}

function focusMainContent() {
  document.getElementById("contenido")?.focus();
}

export function AppShell({ center, end, children }: AppShellProps) {
  return (
    <div className="flex min-h-dvh flex-col">
      {/* Botón y no enlace: un href="#…" chocaría con las rutas por hash. */}
      <button
        type="button"
        onClick={focusMainContent}
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:rounded-control focus:bg-surface focus:px-4 focus:py-2.5 focus:font-semibold"
      >
        Saltar al contenido
      </button>

      <header className={cx(PAGE_CONTAINER, "grid grid-cols-[1fr_auto_1fr] items-center gap-3 py-5 sm:py-6")}>
        <div className="justify-self-start">
          <Brand />
        </div>
        <div className="justify-self-center">{center}</div>
        <div className="flex items-center gap-2 justify-self-end">{end}</div>
      </header>

      <main id="contenido" tabIndex={-1} className={cx(PAGE_CONTAINER, "flex-1 pt-2 pb-10 outline-none sm:pt-6")}>
        {children}
      </main>
    </div>
  );
}
