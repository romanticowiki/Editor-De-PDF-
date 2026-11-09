import { isRecord } from "../lib/guards";
import type { NRect, Rgb } from "../components/editor/types";
import { ApiError, type FileDownload, requestFile, requestJson } from "./apiClient";

export interface EditorPage {
  number: number;
  /** Ancho/alto de la página en PUNTOS PDF (para mapear coordenadas). */
  width: number;
  height: number;
  /** data URL JPEG generada por el motor local. */
  image: string;
  hasFormFields: boolean;
  fields: EditorFormField[];
}

export interface EditorFormField {
  name: string;
  label: string;
  kind: "text" | "checkbox" | "radio" | "choice";
  value: string | boolean;
  rect: NRect;
  size: number;
  multiline: boolean;
  readOnly: boolean;
  options: string[];
  color: Rgb | null;
  font: string;
}

let fontPromise: Promise<void> | null = null;

function loadEditorFont(): Promise<void> {
  fontPromise ??= requestFile("/editor/font", "editor.ttf").then(async ({ blob }) => {
    const font = await new FontFace("EPDFEditor", await blob.arrayBuffer()).load();
    document.fonts.add(font);
  }).catch((error: unknown) => { fontPromise = null; throw error; });
  return fontPromise;
}

// Rasterizar y procesar documentos largos puede tardar: margen amplio, nunca infinito.
const EDITOR_TIMEOUT_MS = 3 * 60_000;

export async function fetchEditorPages(file: File, signal?: AbortSignal): Promise<EditorPage[]> {
  const body = new FormData();
  body.append("file", file, file.name);
  const [pages] = await Promise.all([requestJson("/editor/preview", parsePages, { method: "POST", body, signal, timeoutMs: EDITOR_TIMEOUT_MS }), loadEditorFont()]);
  return pages;
}

export function processEditor(
  file: File,
  operationsJson: string,
  images: readonly Blob[],
  signal?: AbortSignal,
): Promise<FileDownload> {
  const body = new FormData();
  body.append("file", file, file.name);
  body.append("operations", operationsJson);
  images.forEach((blob, index) => body.append("images", blob, `imagen-${index}.${blob.type === "image/jpeg" ? "jpg" : "png"}`));
  return requestFile("/editor/process", "documento-editado.pdf", {
    method: "POST",
    body,
    signal,
    timeoutMs: EDITOR_TIMEOUT_MS,
  });
}

function parsePages(data: unknown): EditorPage[] {
  if (!isRecord(data) || !Array.isArray(data.pages)) throw new ApiError("server");
  return data.pages.map(parsePage);
}

function parsePage(raw: unknown): EditorPage {
  if (
    !isRecord(raw) ||
    typeof raw.number !== "number" ||
    typeof raw.width !== "number" ||
    typeof raw.height !== "number" ||
    typeof raw.image !== "string" ||
    !raw.image.startsWith("data:image/")
  ) {
    throw new ApiError("server");
  }
  if (raw.fields !== undefined && !Array.isArray(raw.fields)) throw new ApiError("server");
  const fields = (raw.fields as unknown[] | undefined)?.map(parseField) ?? [];
  return { number: raw.number, width: raw.width, height: raw.height, image: raw.image, hasFormFields: raw.has_form_fields === true || fields.length > 0, fields };
}

function parseField(raw: unknown): EditorFormField {
  if (!isRecord(raw) || typeof raw.name !== "string" || !["text", "checkbox", "radio", "choice"].includes(String(raw.kind)) || (typeof raw.value !== "string" && typeof raw.value !== "boolean") || !isRecord(raw.rect) || typeof raw.size !== "number" || !Number.isFinite(raw.size) || !Array.isArray(raw.options) || !raw.options.every((item) => typeof item === "string")) throw new ApiError("server");
  const rect = raw.rect;
  if (![rect.x0, rect.y0, rect.x1, rect.y1].every((item) => typeof item === "number" && Number.isFinite(item) && item >= 0 && item <= 1) || Number(rect.x1) <= Number(rect.x0) || Number(rect.y1) <= Number(rect.y0)) throw new ApiError("server");
  const color = Array.isArray(raw.color) && raw.color.length === 3 && raw.color.every((c) => typeof c === "number" && Number.isFinite(c) && c >= 0 && c <= 1) ? raw.color as unknown as Rgb : null;
  return { name: raw.name, label: typeof raw.label === "string" ? raw.label : raw.name, kind: raw.kind as EditorFormField["kind"], value: raw.value, rect: rect as unknown as NRect, size: raw.size, multiline: raw.multiline === true, readOnly: raw.read_only === true, options: raw.options as string[], color, font: typeof raw.font === "string" ? raw.font : "Helv" };
}
