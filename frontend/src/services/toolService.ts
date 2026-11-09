import { type FileDownload, requestFile } from "./apiClient";

// Convertir documentos grandes puede tardar: margen amplio, pero nunca infinito.
const TOOL_TIMEOUT_MS = 5 * 60_000;
const FALLBACK_FILENAME = "resultado";

interface SubmitOptions {
  fields?: Readonly<Record<string, string>>;
  /** Nombre del campo multipart: "file" para herramientas de un archivo, "files" para varias. */
  fileField?: "file" | "files";
  signal?: AbortSignal;
}

export function submitTool(endpoint: string, files: readonly File[], options: SubmitOptions = {}): Promise<FileDownload> {
  const { fields = {}, fileField = "file", signal } = options;
  const body = new FormData();
  for (const file of files) body.append(fileField, file, file.name);
  for (const [name, value] of Object.entries(fields)) body.append(name, value);

  return requestFile(endpoint, FALLBACK_FILENAME, { method: "POST", body, signal, timeoutMs: TOOL_TIMEOUT_MS });
}
