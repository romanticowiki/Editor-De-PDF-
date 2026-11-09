import { motion } from "motion/react";
import { useMemo, useState } from "react";

import { MAX_MERGE_FILES, MAX_UPLOAD_BYTES } from "../../config/limits";
import {
  FAILURE_TITLE,
  WORKING_COPY,
  apiErrorToast,
  multiFileBlocker,
  rejectionToast,
  successToast,
  uploadHint,
} from "../../copy/messages";
import type { ApiHealth } from "../../hooks/useApiHealth";
import { useFileQueue } from "../../hooks/useFileQueue";
import { useToolJob } from "../../hooks/useToolJob";
import { initialFieldValues, submittableFields } from "../../lib/fields";
import { type FileLimits, formatBytes } from "../../lib/files";
import { submitTool } from "../../services/toolService";
import type { MultiFileToolDefinition, ToolField } from "../../tools/types";
import { Dropzone } from "../dropzone/Dropzone";
import { useToast } from "../toast/toastContext";
import { ActionPanel } from "../tool/ActionPanel";
import { ToolFields } from "../tool/ToolFields";
import { ToolWorkspace } from "../tool/ToolWorkspace";
import { Button } from "../ui/Button";
import { FileList } from "./FileList";

const NO_FIELDS: readonly ToolField[] = [];

/** Varios archivos en una lista ordenable: unir PDF, imágenes a PDF… */
export function MultiFileTool({ tool, apiHealth }: { tool: MultiFileToolDefinition; apiHealth: ApiHealth }) {
  const { notify } = useToast();
  const fields = tool.fields ?? NO_FIELDS;
  // Estable mientras la vista vive (cambiar de herramienta la vuelve a montar).
  const limits = useMemo<FileLimits>(
    () => ({ maxFiles: MAX_MERGE_FILES, maxFileBytes: MAX_UPLOAD_BYTES, accept: tool.accept }),
    [tool.accept],
  );
  const { items, addFiles, removeFile, moveFile, reorder, clear } = useFileQueue(limits);
  const [values, setValues] = useState(() => initialFieldValues(fields));
  const { isRunning, run, cancel } = useToolJob();

  const totalBytes = useMemo(() => items.reduce((sum, { file }) => sum + file.size, 0), [items]);
  const hasFiles = items.length > 0;
  const blocker = multiFileBlocker(items.length, tool.minFiles, apiHealth === "offline");
  const status =
    blocker ?? (isRunning ? WORKING_COPY : "Arrastra desde el asa o usa las flechas para cambiar el orden.");

  const handleFiles = (incoming: File[]) => {
    const rejected = addFiles(incoming);
    if (rejected.length > 0) notify(rejectionToast(rejected, { acceptLabel: tool.accept.label, maxFiles: MAX_MERGE_FILES }));
  };

  const handleRun = async () => {
    const files = items.map(({ file }) => file);
    const payload = submittableFields(fields, values);
    const outcome = await run((signal) => submitTool(tool.endpoint, files, { fileField: "files", fields: payload, signal }));
    notify(outcome.ok ? successToast(outcome.download) : apiErrorToast(outcome.error, FAILURE_TITLE));
  };

  return (
    <ToolWorkspace
      asideLabel="Resumen y acción"
      main={
        <>
          <Dropzone
            accept={tool.accept}
            hint={uploadHint(tool.accept, MAX_MERGE_FILES)}
            multiple
            compact={hasFiles}
            disabled={isRunning}
            onFiles={handleFiles}
          />
          {hasFiles && (
            // Solo la lista se desplaza: «Añadir más archivos» sigue arriba a la vista.
            <motion.div layoutScroll className="mt-2 min-h-0 flex-1 overflow-y-auto overscroll-contain p-0.5">
              <FileList items={items} disabled={isRunning} onReorder={reorder} onMove={moveFile} onRemove={removeFile} />
            </motion.div>
          )}
        </>
      }
      aside={
        <ActionPanel
          status={status}
          canRun={blocker === null}
          isRunning={isRunning}
          actionLabel={tool.actionLabel}
          workingLabel={tool.workingLabel}
          onRun={() => void handleRun()}
          onCancel={cancel}
          secondaryAction={
            hasFiles ? (
              <Button variant="quiet" onClick={clear} className="w-full">
                Vaciar lista
              </Button>
            ) : null
          }
        >
          <dl className="grid shrink-0 grid-cols-2 gap-2">
            <SummaryItem label="Archivos" value={String(items.length)} />
            <SummaryItem label="Peso total" value={formatBytes(totalBytes)} />
          </dl>
          {fields.length > 0 && (
            <ToolFields
              fields={fields}
              values={values}
              disabled={isRunning}
              onChange={(name, value) => setValues((current) => ({ ...current, [name]: value }))}
            />
          )}
        </ActionPanel>
      }
    />
  );
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5 rounded-control border border-line/60 bg-surface/70 p-3.5">
      <dt className="text-[0.8125rem] text-muted">{label}</dt>
      <dd className="text-2xl font-semibold tracking-[-0.02em] text-ink tabular-nums">{value}</dd>
    </div>
  );
}
