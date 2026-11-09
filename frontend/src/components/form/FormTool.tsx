import { useEffect, useMemo, useState } from "react";

import {
  FAILURE_TITLE,
  FORM_COPY,
  READY_COPY,
  WORKING_COPY,
  apiErrorToast,
  plural,
  rejectionToast,
  successToast,
  uploadHint,
} from "../../copy/messages";
import type { ApiHealth } from "../../hooks/useApiHealth";
import { useFileAnalysis } from "../../hooks/useFileAnalysis";
import { useSelectedFile } from "../../hooks/useSelectedFile";
import { useToolJob } from "../../hooks/useToolJob";
import { type FormFieldInfo, type FormValue, fetchFormFields } from "../../services/formsService";
import { submitTool } from "../../services/toolService";
import { PDF_ACCEPT } from "../../tools/accept";
import type { FormToolDefinition } from "../../tools/types";
import { Dropzone } from "../dropzone/Dropzone";
import { useToast } from "../toast/toastContext";
import { ActionPanel } from "../tool/ActionPanel";
import { LoadedFileHeader } from "../tool/LoadedFileHeader";
import { ReplaceDropArea } from "../tool/ReplaceDropArea";
import { ToolWorkspace } from "../tool/ToolWorkspace";
import { CheckboxCard } from "../ui/CheckboxCard";
import { FormFieldInput } from "./FormFieldInput";

const NO_FIELDS: readonly FormFieldInfo[] = [];
const ENGINE_OFFLINE_COPY = "El motor local está apagado. Ejecuta scripts\\start.ps1 y vuelve aquí.";

export function FormTool({ tool, apiHealth }: { tool: FormToolDefinition; apiHealth: ApiHealth }) {
  const { notify } = useToast();
  const { file, select, clear } = useSelectedFile(PDF_ACCEPT);
  const analysis = useFileAnalysis(file, fetchFormFields);
  const [values, setValues] = useState<Record<string, FormValue>>({});
  const [flatten, setFlatten] = useState(false);
  const { isRunning, run, cancel } = useToolJob();

  const fields = analysis.status === "ready" ? analysis.data : NO_FIELDS;
  const editableFields = fields.filter((field) => !field.readOnly);
  const fieldsByPage = useMemo(() => groupByPage(fields), [fields]);

  useEffect(() => {
    if (analysis.status === "ready") {
      setValues(Object.fromEntries(analysis.data.filter((field) => !field.readOnly).map((field) => [field.name, field.value])));
    } else if (analysis.status === "error") {
      notify(apiErrorToast(analysis.error, "No pudimos leer el formulario"));
      clear();
    }
  }, [analysis, notify, clear]);

  const isReady = analysis.status === "ready";
  const blocker = !file
    ? "Elige un formulario PDF para empezar."
    : !isReady
      ? FORM_COPY.loading
      : fields.length === 0
        ? FORM_COPY.empty
        : editableFields.length === 0
          ? FORM_COPY.noEditableFields
          : apiHealth === "offline"
            ? ENGINE_OFFLINE_COPY
            : null;
  const status = blocker ?? (isRunning ? WORKING_COPY : READY_COPY);

  const handleFiles = (incoming: File[]) => {
    const rejected = select(incoming);
    if (rejected.length > 0) notify(rejectionToast(rejected, { acceptLabel: PDF_ACCEPT.label, maxFiles: 1 }));
  };

  const handleRun = async () => {
    if (!file) return;
    const payload = { values: JSON.stringify(values), flatten: String(flatten) };
    const outcome = await run((signal) => submitTool("/forms/fill", [file], { fields: payload, signal }));
    notify(outcome.ok ? successToast(outcome.download) : apiErrorToast(outcome.error, FAILURE_TITLE));
  };

  return (
    <ToolWorkspace
      asideLabel="Opciones y acción"
      main={
        file ? (
          <ReplaceDropArea disabled={isRunning} onFiles={handleFiles}>
            <LoadedFileHeader
              file={file}
              detail={isReady ? plural(fields.length, "campo", "campos") : "Leyendo…"}
              accept={PDF_ACCEPT}
              disabled={isRunning}
              onFiles={handleFiles}
              onRemove={clear}
            />
            <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain rounded-panel bg-surface-sunken/80 p-4 sm:p-5">
              {!isReady ? (
                <FormSkeleton />
              ) : fields.length === 0 ? (
                <p className="py-12 text-center text-[0.9375rem] text-muted">{FORM_COPY.empty}</p>
              ) : (
                fieldsByPage.map(([page, pageFields]) => (
                  <section key={page} className="mb-7 last:mb-0">
                    <h2 className="mb-3 text-[0.75rem] font-bold tracking-[0.12em] text-muted uppercase">Página {page}</h2>
                    <div className="grid gap-4 md:grid-cols-2">
                      {pageFields.map((field) => (
                        <FormFieldInput
                          key={field.name}
                          field={field}
                          value={field.readOnly ? field.value : values[field.name]}
                          disabled={isRunning}
                          onChange={(value) => setValues((current) => ({ ...current, [field.name]: value }))}
                        />
                      ))}
                    </div>
                  </section>
                ))
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
          canRun={blocker === null}
          isRunning={isRunning}
          actionLabel={tool.actionLabel}
          workingLabel={tool.workingLabel}
          onRun={() => void handleRun()}
          onCancel={cancel}
        >
          <CheckboxCard
            label={FORM_COPY.flattenLabel}
            description={FORM_COPY.flattenDescription}
            checked={flatten}
            disabled={isRunning}
            onChange={setFlatten}
          />
        </ActionPanel>
      }
    />
  );
}

function groupByPage(fields: readonly FormFieldInfo[]): Array<[number, FormFieldInfo[]]> {
  const groups = new Map<number, FormFieldInfo[]>();
  for (const field of fields) groups.set(field.page, [...(groups.get(field.page) ?? []), field]);
  return [...groups.entries()].sort(([a], [b]) => a - b);
}

function FormSkeleton() {
  return (
    <div aria-hidden className="grid gap-4 md:grid-cols-2">
      {Array.from({ length: 4 }, (_, index) => (
        <div key={index} className="flex flex-col gap-2">
          <span className="h-3 w-24 rounded bg-line/50 motion-safe:animate-pulse" />
          <span className="h-11 rounded-control bg-line/40 motion-safe:animate-pulse" />
        </div>
      ))}
    </div>
  );
}
