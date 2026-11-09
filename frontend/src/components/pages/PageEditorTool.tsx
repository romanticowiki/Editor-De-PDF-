import { RotateCcw, RotateCw, Undo2 } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";

import {
  FAILURE_TITLE,
  PAGE_EDITOR_HINT,
  WORKING_COPY,
  apiErrorToast,
  pageEditorBlocker,
  pageEditorSummary,
  plural,
  rejectionToast,
  successToast,
  uploadHint,
  zipSummary,
} from "../../copy/messages";
import type { ApiHealth } from "../../hooks/useApiHealth";
import { useFileAnalysis } from "../../hooks/useFileAnalysis";
import { useSelectedFile } from "../../hooks/useSelectedFile";
import { useToolJob } from "../../hooks/useToolJob";
import {
  type EditablePage,
  buildInstructions,
  countPages,
  createPages,
  rotatePages,
  selectAllPages,
  togglePage,
} from "../../lib/pageEditor";
import { fetchPagePreview } from "../../services/pagesService";
import { submitTool } from "../../services/toolService";
import { PDF_ACCEPT } from "../../tools/accept";
import { EXTRACT_OUTPUT } from "../../tools/fields";
import type { PageEditorMode, PageToolDefinition } from "../../tools/types";
import { Dropzone } from "../dropzone/Dropzone";
import { useToast } from "../toast/toastContext";
import { ActionPanel } from "../tool/ActionPanel";
import { LoadedFileHeader } from "../tool/LoadedFileHeader";
import { ReplaceDropArea } from "../tool/ReplaceDropArea";
import { ToolWorkspace } from "../tool/ToolWorkspace";
import { Button } from "../ui/Button";
import { ChoiceCards } from "../ui/ChoiceCards";
import { FIELD_LABEL } from "../ui/inputStyles";
import { PageGrid, PageGridSkeleton } from "./PageGrid";

const PAGES_SUMMARY = zipSummary({ singular: "archivo", plural: "archivos" });

/** Girar, eliminar, extraer y organizar: la misma vista con distinta interacción por modo. */
export function PageEditorTool({ tool, apiHealth }: { tool: PageToolDefinition; apiHealth: ApiHealth }) {
  const { notify } = useToast();
  const { file, select, clear } = useSelectedFile(PDF_ACCEPT);
  const analysis = useFileAnalysis(file, fetchPagePreview);
  const [pages, setPages] = useState<EditablePage[]>([]);
  const [output, setOutput] = useState(EXTRACT_OUTPUT.defaultValue);
  const { isRunning, run, cancel } = useToolJob();

  useEffect(() => {
    if (analysis.status === "ready") {
      setPages(createPages(analysis.data));
    } else if (analysis.status === "error") {
      notify(apiErrorToast(analysis.error, "No pudimos abrir el PDF"));
      clear();
    } else {
      setPages([]);
    }
  }, [analysis, notify, clear]);

  const isReady = analysis.status === "ready";
  const counts = countPages(pages);
  const blocker = !file
    ? "Elige un PDF para empezar."
    : !isReady
      ? "Preparando las páginas…"
      : pageEditorBlocker(tool.mode, counts, apiHealth === "offline");
  const status = blocker ?? (isRunning ? WORKING_COPY : pageEditorSummary(tool.mode, counts));

  const handleFiles = (incoming: File[]) => {
    const rejected = select(incoming);
    if (rejected.length > 0) notify(rejectionToast(rejected, { acceptLabel: PDF_ACCEPT.label, maxFiles: 1 }));
  };

  const handleActivate = (id: string) => {
    if (tool.mode === "rotate") setPages((current) => rotatePages(current, 90, id));
    else if (tool.mode === "delete") setPages((current) => togglePage(current, id, "removed"));
    else if (tool.mode === "extract") setPages((current) => togglePage(current, id, "selected"));
  };

  const handleReset = () => {
    if (analysis.status === "ready") setPages(createPages(analysis.data));
  };

  const handleRun = async () => {
    if (!file) return;
    const fields = {
      pages: JSON.stringify(buildInstructions(tool.mode, pages)),
      output: tool.mode === "extract" ? output : "single",
    };
    const outcome = await run((signal) => submitTool("/pages/organize", [file], { fields, signal }));
    notify(
      outcome.ok ? successToast(outcome.download, PAGES_SUMMARY(outcome.download)) : apiErrorToast(outcome.error, FAILURE_TITLE),
    );
  };

  return (
    <ToolWorkspace
      asideLabel="Resumen y acción"
      main={
        file ? (
          <ReplaceDropArea disabled={isRunning} onFiles={handleFiles}>
            <LoadedFileHeader
              file={file}
              detail={isReady ? plural(pages.length, "página", "páginas") : "Preparando…"}
              accept={PDF_ACCEPT}
              disabled={isRunning}
              onFiles={handleFiles}
              onRemove={clear}
            />
            <p className="shrink-0 px-2 pb-3 text-sm text-muted">{PAGE_EDITOR_HINT[tool.mode]}</p>
            <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain rounded-panel bg-surface-sunken/80 p-3 sm:p-4">
              {isReady ? (
                <PageGrid
                  pages={pages}
                  mode={tool.mode}
                  disabled={isRunning}
                  onActivate={handleActivate}
                  onRotate={(id, delta) => setPages((current) => rotatePages(current, delta, id))}
                  onToggleRemoved={(id) => setPages((current) => togglePage(current, id, "removed"))}
                  onReorder={setPages}
                />
              ) : (
                <PageGridSkeleton />
              )}
            </div>
          </ReplaceDropArea>
        ) : (
          <Dropzone accept={PDF_ACCEPT} hint={uploadHint(PDF_ACCEPT, 1)} disabled={isRunning} onFiles={handleFiles} />
        )
      }
      aside={
        <ActionPanel
          status={status}
          canRun={isReady && blocker === null}
          isRunning={isRunning}
          actionLabel={tool.actionLabel}
          workingLabel={tool.workingLabel}
          onRun={() => void handleRun()}
          onCancel={cancel}
        >
          {tool.mode === "extract" && (
            <ChoiceCards field={EXTRACT_OUTPUT} value={output} disabled={isRunning} onChange={setOutput} />
          )}
          {isReady && (
            <QuickActions
              mode={tool.mode}
              disabled={isRunning}
              onRotateAll={(delta) => setPages((current) => rotatePages(current, delta))}
              onSelectAll={(selected) => setPages((current) => selectAllPages(current, selected))}
              onReset={handleReset}
            />
          )}
        </ActionPanel>
      }
    />
  );
}

interface QuickActionsProps {
  mode: PageEditorMode;
  disabled: boolean;
  onRotateAll: (delta: 90 | -90) => void;
  onSelectAll: (selected: boolean) => void;
  onReset: () => void;
}

function QuickActions({ mode, disabled, onRotateAll, onSelectAll, onReset }: QuickActionsProps) {
  const canRotate = mode === "organize" || mode === "rotate";

  return (
    <div className="flex flex-col gap-2">
      <p className={FIELD_LABEL}>Acciones rápidas</p>
      <div className="flex flex-wrap gap-2">
        {canRotate && (
          <>
            <QuickButton icon={<RotateCcw className="size-4" aria-hidden />} disabled={disabled} onClick={() => onRotateAll(-90)}>
              Todas a la izquierda
            </QuickButton>
            <QuickButton icon={<RotateCw className="size-4" aria-hidden />} disabled={disabled} onClick={() => onRotateAll(90)}>
              Todas a la derecha
            </QuickButton>
          </>
        )}
        {mode === "extract" && (
          <>
            <QuickButton disabled={disabled} onClick={() => onSelectAll(true)}>
              Elegir todas
            </QuickButton>
            <QuickButton disabled={disabled} onClick={() => onSelectAll(false)}>
              Ninguna
            </QuickButton>
          </>
        )}
        <QuickButton icon={<Undo2 className="size-4" aria-hidden />} disabled={disabled} onClick={onReset}>
          Deshacer cambios
        </QuickButton>
      </div>
    </div>
  );
}

function QuickButton({
  icon,
  disabled,
  onClick,
  children,
}: {
  icon?: ReactNode;
  disabled: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <Button variant="quiet" icon={icon} disabled={disabled} onClick={onClick} className="h-9 border border-line/70 px-3 text-sm">
      {children}
    </Button>
  );
}
