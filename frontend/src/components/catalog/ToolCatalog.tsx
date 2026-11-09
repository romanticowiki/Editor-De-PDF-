import { motion } from "motion/react";
import { useMemo } from "react";

import { springs } from "../../lib/motion";
import type { EngineAvailability } from "../../services/engineService";
import { TOOLS, filterTools, groupByCategory } from "../../tools/catalog";
import { ToolCard } from "./ToolCard";

interface ToolCatalogProps {
  query: string;
  engines: EngineAvailability;
  onNavigate?: () => void;
}

const MAX_STAGGER_SECONDS = 0.4;

export function ToolCatalog({ query, engines, onNavigate }: ToolCatalogProps) {
  const groups = useMemo(() => groupByCategory(filterTools(TOOLS, query)), [query]);

  if (groups.length === 0) {
    return (
      <p role="status" className="px-4 py-16 text-center text-[0.9375rem] text-muted">
        No encontramos «{query.trim()}». Prueba con otra palabra.
      </p>
    );
  }

  return (
    // Columnas CSS: las categorías se reparten solas aunque tengan distinta cantidad de herramientas.
    <div className="gap-6 sm:columns-2 lg:columns-3 xl:gap-10">
      {groups.map(({ category, tools }, groupIndex) => (
        <section key={category.id} className="mb-6 break-inside-avoid last:mb-0 sm:mb-8">
          <h2 className="mb-2 px-2.5 text-[0.75rem] font-bold tracking-[0.12em] text-muted uppercase">{category.title}</h2>
          <ul className="flex flex-col gap-0.5">
            {tools.map((tool, index) => (
              <motion.li
                key={tool.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ ...springs.snappy, delay: Math.min(groupIndex * 0.04 + index * 0.025, MAX_STAGGER_SECONDS) }}
              >
                <ToolCard tool={tool} engines={engines} onNavigate={onNavigate} />
              </motion.li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
