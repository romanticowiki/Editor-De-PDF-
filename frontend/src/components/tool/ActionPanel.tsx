import { Download } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "../ui/Button";

interface ActionPanelProps {
  /** Opciones o resumen de la herramienta, encima de la acción. */
  children?: ReactNode;
  status: string;
  canRun: boolean;
  isRunning: boolean;
  actionLabel: string;
  workingLabel: string;
  onRun: () => void;
  onCancel: () => void;
  secondaryAction?: ReactNode;
}

export function ActionPanel({
  children,
  status,
  canRun,
  isRunning,
  actionLabel,
  workingLabel,
  onRun,
  onCancel,
  secondaryAction,
}: ActionPanelProps) {
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-5">
      {children && (
        // Si hay muchas opciones, se desplazan ellas: el botón de acción queda siempre a la vista.
        <div className="-mx-1 flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto overscroll-contain px-1 pt-1 pb-1">
          {children}
        </div>
      )}
      <div className="flex shrink-0 flex-col gap-3">
        <p aria-live="polite" className="text-sm leading-relaxed text-muted text-pretty">
          {status}
        </p>
        <Button
          onClick={onRun}
          disabled={!canRun}
          isLoading={isRunning}
          icon={<Download className="size-[1.125rem]" aria-hidden />}
          className="w-full"
        >
          {isRunning ? workingLabel : actionLabel}
        </Button>
        {isRunning ? (
          <Button variant="quiet" onClick={onCancel} className="w-full">
            Cancelar
          </Button>
        ) : (
          secondaryAction
        )}
      </div>
    </div>
  );
}
