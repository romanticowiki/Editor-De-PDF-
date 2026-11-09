import { motion } from "motion/react";
import type { ReactNode } from "react";

import { springs } from "../../lib/motion";

interface ToolWorkspaceProps {
  main: ReactNode;
  aside: ReactNode;
  asideLabel: string;
}

/**
 * Zona de trabajo + panel de acción.
 * En escritorio ocupa exactamente la altura disponible: las listas largas se desplazan por dentro
 * y el panel con el botón nunca sale de la pantalla. En móvil todo fluye en una columna.
 */
export function ToolWorkspace({ main, aside, asideLabel }: ToolWorkspaceProps) {
  return (
    <div className="grid gap-5 lg:h-full lg:grid-cols-[minmax(0,1fr)_22rem] lg:grid-rows-[minmax(0,1fr)] lg:gap-6 xl:grid-cols-[minmax(0,1fr)_24rem]">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={springs.gentle}
        className="glass flex min-h-0 min-w-0 flex-col rounded-card p-2"
      >
        {main}
      </motion.div>
      <motion.aside
        aria-label={asideLabel}
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...springs.gentle, delay: 0.06 }}
        className="glass flex min-h-0 flex-col self-start rounded-card p-5 sm:p-6 lg:max-h-full"
      >
        {aside}
      </motion.aside>
    </div>
  );
}
