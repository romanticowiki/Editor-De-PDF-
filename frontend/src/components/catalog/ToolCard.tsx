import { ChevronRight } from "lucide-react";

import { ENGINE_COPY } from "../../copy/messages";
import type { EngineAvailability } from "../../services/engineService";
import { TOOL_CATEGORIES, missingEngine } from "../../tools/catalog";
import type { ToolDefinition } from "../../tools/types";
import { ToolIcon } from "./ToolIcon";

interface ToolCardProps {
  tool: ToolDefinition;
  engines: EngineAvailability;
  onNavigate?: () => void;
}

export function ToolCard({ tool, engines, onNavigate }: ToolCardProps) {
  const missing = missingEngine(tool, engines);

  return (
    <a
      href={`#/${tool.slug}`}
      onClick={onNavigate}
      className="group flex items-center gap-3.5 rounded-panel p-2.5 transition-[background-color,transform] duration-200 ease-out-quart hover:bg-surface/80 active:scale-[0.98]"
    >
      <ToolIcon icon={tool.icon} tone={TOOL_CATEGORIES[tool.category].tone} />
      <span className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className="text-[0.9375rem] font-semibold tracking-[-0.01em] text-ink">{tool.title}</span>
          {missing && (
            <span className="rounded-full bg-warning-soft px-2 py-0.5 text-[0.75rem] font-semibold text-warning">
              {ENGINE_COPY[missing].badge}
            </span>
          )}
        </span>
        <span className="text-[0.8125rem] leading-snug text-muted">{tool.description}</span>
      </span>
      <ChevronRight
        className="size-4 -translate-x-1 text-muted opacity-0 transition-[opacity,transform] duration-200 ease-out-quart group-hover:translate-x-0 group-hover:opacity-100"
        aria-hidden
      />
    </a>
  );
}
