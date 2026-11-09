import { LayoutGrid, X } from "lucide-react";
import { motion } from "motion/react";
import { useCallback, useEffect, useRef, useState } from "react";

import { springs } from "../../lib/motion";
import type { EngineAvailability } from "../../services/engineService";
import { IconButton } from "../ui/IconButton";
import { SearchField } from "../ui/SearchField";
import { ToolCatalog } from "./ToolCatalog";

/** Menú central de herramientas. Usa <dialog> nativo: foco atrapado, Esc y capa superior sin código extra. */
export function ToolsMenu({ engines }: { engines: EngineAvailability }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  // Cambia en cada apertura: repite la animación de entrada y dispara el enfoque del buscador.
  const [openCount, setOpenCount] = useState(0);

  const open = useCallback(() => {
    const dialog = dialogRef.current;
    if (!dialog || dialog.open) return;
    setQuery("");
    setOpenCount((count) => count + 1);
    dialog.showModal();
  }, []);

  const close = useCallback(() => dialogRef.current?.close(), []);

  useEffect(() => {
    if (openCount > 0) searchRef.current?.focus();
  }, [openCount]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        open();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open]);

  return (
    <>
      <button
        type="button"
        onClick={open}
        aria-haspopup="dialog"
        className="glass inline-flex h-10 items-center gap-2 rounded-full px-3 text-[0.875rem] font-semibold text-ink-soft [--glass-alpha:0.55] transition-[color,transform] duration-150 ease-out-quart hover:text-ink active:scale-[0.97] sm:px-4"
      >
        <LayoutGrid className="size-4" aria-hidden />
        <span className="sr-only sm:not-sr-only">Todas las herramientas</span>
        <kbd className="hidden rounded-md border border-line px-1.5 py-0.5 font-sans text-[0.75rem] font-semibold text-muted lg:inline">
          Ctrl K
        </kbd>
      </button>

      <dialog
        ref={dialogRef}
        aria-label="Todas las herramientas"
        // Un clic fuera del panel (en el fondo) cierra el menú.
        onClick={(event) => {
          if (event.target === event.currentTarget) close();
        }}
        className="m-auto max-h-[min(46rem,calc(100dvh-2rem))] w-[min(68rem,calc(100vw-2rem))] overflow-hidden rounded-card bg-transparent p-0 text-ink backdrop:bg-[rgb(var(--shadow-rgb)/0.35)] backdrop:backdrop-blur-[2px]"
      >
        <motion.div
          key={openCount}
          initial={{ opacity: 0, scale: 0.97, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={springs.snappy}
          className="glass flex max-h-[inherit] flex-col rounded-card [--glass-alpha:0.97]"
        >
          <div className="flex items-center gap-3 border-b border-line/60 p-3 sm:p-4">
            <SearchField value={query} onChange={setQuery} variant="plain" inputRef={searchRef} />
            <IconButton label="Cerrar" round onClick={close}>
              <X className="size-[1.125rem]" aria-hidden />
            </IconButton>
          </div>
          <div className="overflow-y-auto overscroll-contain p-3 sm:p-6">
            <ToolCatalog query={query} engines={engines} onNavigate={close} />
          </div>
        </motion.div>
      </dialog>
    </>
  );
}
