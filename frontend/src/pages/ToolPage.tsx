import { ChevronRight } from "lucide-react";
import { motion } from "motion/react";

import { ToolIcon } from "../components/catalog/ToolIcon";
import { PDFEditorStudio } from "../components/editor/PDFEditorStudio";
import { FormTool } from "../components/form/FormTool";
import { MultiFileTool } from "../components/multi/MultiFileTool";
import { PageEditorTool } from "../components/pages/PageEditorTool";
import { FileTool } from "../components/tool/FileTool";
import type { ApiHealth } from "../hooks/useApiHealth";
import { springs } from "../lib/motion";
import type { EngineAvailability } from "../services/engineService";
import { TOOL_CATEGORIES } from "../tools/catalog";
import type { ToolDefinition } from "../tools/types";

interface ToolPageProps {
  tool: ToolDefinition;
  apiHealth: ApiHealth;
  engines: EngineAvailability;
}

export function ToolPage({ tool, apiHealth, engines }: ToolPageProps) {
  const category = TOOL_CATEGORIES[tool.category];

  return (
    // En escritorio la página ocupa justo la altura visible (cabecera de la app ≈ 9.5rem):
    // la herramienta cabe entera sin desplazar la ventana. En pantallas bajas, mínimo 32rem.
    <div className="flex flex-col gap-5 lg:h-[calc(100dvh-9.5rem)] lg:min-h-[32rem] lg:gap-6">
      <motion.header
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={springs.gentle}
        className="flex shrink-0 flex-col gap-3 lg:flex-row lg:items-end lg:justify-between lg:gap-10"
      >
        <div className="flex min-w-0 items-center gap-4">
          <ToolIcon icon={tool.icon} tone={category.tone} size="lg" />
          <div className="flex min-w-0 flex-col gap-1">
            <nav aria-label="Ruta" className="flex items-center gap-1.5 text-[0.75rem] font-bold tracking-[0.12em] uppercase">
              <a href="#/" className="text-muted transition-colors duration-150 hover:text-ink">
                Inicio
              </a>
              <ChevronRight className="size-3 text-subtle" aria-hidden />
              <span className="text-accent">{category.title}</span>
            </nav>
            <h1 className="text-[1.75rem] leading-[1.1] font-semibold tracking-[-0.03em] text-balance sm:text-[2.25rem]">
              {tool.title}
            </h1>
          </div>
        </div>
        <p className="max-w-[46ch] text-[0.9375rem] leading-relaxed text-muted text-pretty lg:pb-1 lg:text-right">
          {tool.description}
        </p>
      </motion.header>

      <div className="flex min-h-0 flex-col lg:flex-1">
        <ToolBody tool={tool} apiHealth={apiHealth} engines={engines} />
      </div>
    </div>
  );
}

function ToolBody({ tool, apiHealth, engines }: ToolPageProps) {
  switch (tool.kind) {
    case "file":
      return <FileTool tool={tool} apiHealth={apiHealth} engines={engines} />;
    case "multi":
      return <MultiFileTool tool={tool} apiHealth={apiHealth} />;
    case "pages":
      return <PageEditorTool tool={tool} apiHealth={apiHealth} />;
    case "form":
      return <FormTool tool={tool} apiHealth={apiHealth} />;
    case "editor":
      return <PDFEditorStudio tool={tool} apiHealth={apiHealth} />;
  }
}
