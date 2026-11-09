import { useState } from "react";

import {
  FAILURE_TITLE,
  READY_COPY,
  WORKING_COPY,
  apiErrorToast,
  fileToolBlocker,
  rejectionToast,
  successToast,
  uploadHint,
} from "../../copy/messages";
import type { ApiHealth } from "../../hooks/useApiHealth";
import { useSelectedFile } from "../../hooks/useSelectedFile";
import { useToolJob } from "../../hooks/useToolJob";
import { applyFieldChange, firstFieldError, initialFieldValues, submittableFields } from "../../lib/fields";
import type { EngineAvailability } from "../../services/engineService";
import { submitTool } from "../../services/toolService";
import { missingEngine } from "../../tools/catalog";
import type { FileToolDefinition, ToolField } from "../../tools/types";
import { Dropzone } from "../dropzone/Dropzone";
import { useToast } from "../toast/toastContext";
import { ActionPanel } from "./ActionPanel";
import { SelectedFile } from "./SelectedFile";
import { ToolFields } from "./ToolFields";
import { ToolWorkspace } from "./ToolWorkspace";

interface FileToolProps {
  tool: FileToolDefinition;
  apiHealth: ApiHealth;
  engines: EngineAvailability;
}

const NO_FIELDS: readonly ToolField[] = [];

/** Vista genérica «un archivo entra, un archivo sale». Toda herramienta de tipo `file` la reutiliza. */
export function FileTool({ tool, apiHealth, engines }: FileToolProps) {
  const { notify } = useToast();
  const fields = tool.fields ?? NO_FIELDS;
  const { file, select, clear } = useSelectedFile(tool.accept);
  const [values, setValues] = useState(() => initialFieldValues(fields));
  const { isRunning, run, cancel } = useToolJob();

  const blocker = fileToolBlocker({
    hasFile: file !== null,
    isEngineOffline: apiHealth === "offline",
    missingEngine: missingEngine(tool, engines),
    fieldError: firstFieldError(fields, values),
  });
  const status = blocker ?? (isRunning ? WORKING_COPY : READY_COPY);

  const handleFiles = (incoming: File[]) => {
    const rejected = select(incoming);
    if (rejected.length > 0) notify(rejectionToast(rejected, { acceptLabel: tool.accept.label, maxFiles: 1 }));
  };

  const handleRun = async () => {
    if (!file) return;
    const payload = submittableFields(fields, values, tool.fixedFields);
    const outcome = await run((signal) => submitTool(tool.endpoint, [file], { fields: payload, signal }));
    notify(
      outcome.ok
        ? successToast(outcome.download, tool.describeResult?.(outcome.download))
        : apiErrorToast(outcome.error, FAILURE_TITLE),
    );
  };

  return (
    <ToolWorkspace
      asideLabel="Opciones y acción"
      main={
        file ? (
          <SelectedFile file={file} accept={tool.accept} disabled={isRunning} onFiles={handleFiles} onRemove={clear} />
        ) : (
          <Dropzone accept={tool.accept} hint={uploadHint(tool.accept, 1)} disabled={isRunning} onFiles={handleFiles} />
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
          {fields.length > 0 && (
            <ToolFields
              fields={fields}
              values={values}
              disabled={isRunning}
              onChange={(name, value) => setValues((current) => applyFieldChange(fields, current, name, value))}
            />
          )}
        </ActionPanel>
      }
    />
  );
}
