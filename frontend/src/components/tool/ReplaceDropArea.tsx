import { AnimatePresence, motion } from "motion/react";
import type { ReactNode } from "react";

import { useFileDrop } from "../../hooks/useFileDrop";
import { exitTransition, springs } from "../../lib/motion";

interface ReplaceDropAreaProps {
  disabled: boolean;
  onFiles: (files: File[]) => void;
  children: ReactNode;
}

/** Zona que acepta soltar otro archivo encima para reemplazar el actual. */
export function ReplaceDropArea({ disabled, onFiles, children }: ReplaceDropAreaProps) {
  const { isDragging, dropHandlers } = useFileDrop({ disabled, onFiles });
  const isActive = isDragging && !disabled;

  return (
    <div {...dropHandlers} className="relative flex min-h-0 flex-1 flex-col">
      {children}
      <AnimatePresence>
        {isActive && (
          <motion.div
            initial={{ opacity: 0, scale: 0.99 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, transition: exitTransition }}
            transition={springs.snappy}
            className="pointer-events-none absolute inset-0 flex items-center justify-center rounded-panel border-[1.5px] border-dashed border-accent-ring bg-accent-soft/90 text-base font-semibold text-accent"
          >
            Suelta para reemplazar el archivo
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
