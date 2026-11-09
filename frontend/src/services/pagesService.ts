import { isRecord } from "../lib/guards";
import { ApiError, requestJson } from "./apiClient";

export interface PagePreview {
  number: number;
  width: number;
  height: number;
  /** data URL JPEG generada por el motor local. */
  thumbnail: string;
}

// Documentos de cientos de páginas tardan en generar miniaturas.
const PREVIEW_TIMEOUT_MS = 2 * 60_000;

export function fetchPagePreview(file: File, signal?: AbortSignal): Promise<PagePreview[]> {
  const body = new FormData();
  body.append("file", file, file.name);
  return requestJson("/pages/preview", parsePreview, { method: "POST", body, signal, timeoutMs: PREVIEW_TIMEOUT_MS });
}

function parsePreview(data: unknown): PagePreview[] {
  if (!isRecord(data) || !Array.isArray(data.pages)) throw new ApiError("server");
  return data.pages.map(parsePage);
}

function parsePage(raw: unknown): PagePreview {
  if (
    !isRecord(raw) ||
    typeof raw.number !== "number" ||
    typeof raw.width !== "number" ||
    typeof raw.height !== "number" ||
    typeof raw.thumbnail !== "string" ||
    // Solo imágenes embebidas: nunca una URL que el navegador fuera a pedir.
    !raw.thumbnail.startsWith("data:image/")
  ) {
    throw new ApiError("server");
  }
  return { number: raw.number, width: raw.width, height: raw.height, thumbnail: raw.thumbnail };
}
