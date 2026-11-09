import { motion } from "motion/react";
import { useId, useState } from "react";

import { ToolCatalog } from "../components/catalog/ToolCatalog";
import { SearchField } from "../components/ui/SearchField";
import { springs } from "../lib/motion";
import type { EngineAvailability } from "../services/engineService";

export function HomePage({ engines }: { engines: EngineAvailability }) {
  const titleId = useId();
  const [query, setQuery] = useState("");

  return (
    <section aria-labelledby={titleId} className="flex flex-col items-center gap-8 sm:gap-10">
      <motion.header
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={springs.gentle}
        className="flex max-w-3xl flex-col items-center gap-4 pt-2 text-center sm:pt-6"
      >
        <h1
          id={titleId}
          className="text-[2.25rem] leading-[1.04] font-semibold tracking-[-0.035em] text-balance sm:text-[3.25rem] lg:text-[3.75rem]"
        >
          ¿Qué quieres hacer con tus documentos?
        </h1>
        <p className="text-[1.0625rem] leading-relaxed text-muted text-pretty">Elige una herramienta y empieza en segundos.</p>
      </motion.header>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...springs.gentle, delay: 0.04 }}
        className="w-full max-w-xl"
      >
        <SearchField value={query} onChange={setQuery} />
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...springs.gentle, delay: 0.08 }}
        className="glass w-full rounded-card p-3 sm:p-6 lg:p-8"
      >
        <ToolCatalog query={query} engines={engines} />
      </motion.div>
    </section>
  );
}
