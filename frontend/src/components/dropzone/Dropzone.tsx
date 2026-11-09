import { FileUp } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useId } from "react";

import { useFileDrop } from "../../hooks/useFileDrop";
import { useFilePicker } from "../../hooks/useFilePicker";
import { cx } from "../../lib/cx";
import type { FileAccept } from "../../lib/files";
import { exitTransition, springs } from "../../lib/motion";

interface DropzoneProps {
  accept: FileAccept;
  hint: string;
  onFiles: (files: File[]) => void;
  multiple?: boolean;
  /** Versión en una línea, para cuando ya hay archivos en la lista. */
  compact?: boolean;
  disabled?: boolean;
}

function getTitle(compact: boolean, isActive: boolean, multiple: boolean): string {
  if (compact) return isActive ? "Suéltalos para añadirlos" : "Añadir más archivos";
  if (isActive) return multiple ? "Suéltalos, ya casi está" : "Suéltalo, ya casi está";
  return multiple ? "Suelta tus archivos aquí" : "Suelta tu archivo aquí";
}

export function Dropzone({ accept, hint, onFiles, multiple = false, compact = false, disabled = false }: DropzoneProps) {
  const hintId = useId();
  const { isDragging, dropHandlers } = useFileDrop({ disabled, onFiles });
  const picker = useFilePicker({ accept, multiple, onFiles });
  const isActive = isDragging && !disabled;
  const title = getTitle(compact, isActive, multiple);

  return (
    // Completa, rellena la altura del panel; compacta, solo ocupa su línea.
    <div {...dropHandlers} className={compact ? "shrink-0" : "flex min-h-0 flex-1 flex-col"}>
      <motion.button
        type="button"
        disabled={disabled}
        aria-describedby={hintId}
        onClick={picker.open}
        animate={{ scale: isActive ? 1.012 : 1 }}
        whileTap={{ scale: 0.99 }}
        transition={springs.snappy}
        className={cx(
          "flex w-full items-center rounded-panel border-[1.5px] border-dashed transition-[background-color,border-color] duration-200 ease-out-quart disabled:cursor-not-allowed disabled:opacity-60",
          compact
            ? "gap-4 px-4 py-3.5 text-left"
            : "min-h-72 flex-1 flex-col justify-center gap-5 px-6 py-10 text-center lg:min-h-0",
          isActive
            ? "border-accent-ring bg-accent-soft/80"
            : "border-line bg-surface-sunken/80 hover:border-subtle hover:bg-surface-sunken",
        )}
      >
        <motion.span
          animate={isActive ? { y: -4, scale: 1.08, rotate: -3 } : { y: 0, scale: 1, rotate: 0 }}
          transition={springs.playful}
          className={cx(
            "flex shrink-0 items-center justify-center bg-surface text-accent shadow-lift",
            compact ? "size-11 rounded-[0.75rem]" : "size-20 rounded-[1.375rem]",
          )}
        >
          <FileUp className={compact ? "size-5" : "size-9"} aria-hidden />
        </motion.span>

        <span className={cx("relative flex flex-col", compact ? "gap-0.5" : "items-center gap-1.5")}>
          {/* Nombre accesible estable: el título animado puede convivir un instante con el anterior. */}
          <span className="sr-only">{title}</span>
          <AnimatePresence mode="popLayout" initial={false}>
            <motion.span
              key={title}
              aria-hidden
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4, transition: exitTransition }}
              transition={springs.snappy}
              className={cx(
                "font-semibold text-ink",
                compact ? "text-[0.9375rem] tracking-[-0.01em]" : "text-xl tracking-[-0.02em] sm:text-2xl",
              )}
            >
              {title}
            </motion.span>
          </AnimatePresence>
          {!compact && (
            <span className="text-[0.9375rem] text-muted">{multiple ? "o haz clic para elegirlos" : "o haz clic para elegirlo"}</span>
          )}
          <span id={hintId} className={cx("text-[0.8125rem] text-muted tabular-nums", !compact && "mt-2")}>
            {hint}
          </span>
        </span>
      </motion.button>

      <input {...picker.inputProps} />
    </div>
  );
}
