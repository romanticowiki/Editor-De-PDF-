/**
 * Todo el texto que ve la persona usuaria vive aquí.
 * Tono: frases cortas, sin tecnicismos, sin culpa, siempre con el siguiente paso.
 */

import type { ToastInput } from "../components/toast/types";
import { MAX_UPLOAD_BYTES } from "../config/limits";
import { type FileAccept, type FileRejection, type RejectionReason, formatBytes } from "../lib/files";
import type { ApiError, ApiErrorKind, FileDownload } from "../services/apiClient";
import type { EngineId } from "../services/engineService";
import type { PageEditorMode } from "../tools/types";

export const API_ERROR_COPY: Record<ApiErrorKind, string> = {
  network: "No encontramos el motor local. Comprueba que esté encendido.",
  timeout: "Está tardando más de lo normal. Inténtalo de nuevo.",
  aborted: "Operación cancelada.",
  rate_limited: "Espera un momento y vuelve a intentarlo.",
  client: "No pudimos procesar este archivo.",
  server: "Algo falló en el motor local. Inténtalo de nuevo.",
};

export const FAILURE_TITLE = "No pudimos completarlo";
export const READY_COPY = "Todo listo.";
export const WORKING_COPY = "Esto puede tardar unos segundos.";

const ENGINE_OFFLINE_COPY = "El motor local está apagado. Ejecuta scripts\\start.ps1 y vuelve aquí.";

export const ENGINE_COPY: Record<EngineId, { badge: string; missing: string }> = {
  office: {
    badge: "Necesita Office",
    missing: "Esta herramienta necesita Microsoft Office o LibreOffice instalado en este equipo.",
  },
  ocr: {
    badge: "Necesita Tesseract",
    missing: "El OCR necesita los datos de idioma de Tesseract en este equipo.",
  },
  translate: {
    badge: "Necesita configurar Groq",
    missing: "Traducir necesita una clave de Groq en el archivo .env del motor.",
  },
};

// ——— Archivos ———

interface RejectionContext {
  acceptLabel: string;
  maxFiles: number;
}

function rejectionReasonCopy(reason: RejectionReason, { acceptLabel, maxFiles }: RejectionContext): string {
  switch (reason) {
    case "wrong_type":
      return `Esta herramienta acepta ${acceptLabel}.`;
    case "empty":
      return "El archivo está vacío.";
    case "too_large":
      return `Cada archivo puede pesar hasta ${formatBytes(MAX_UPLOAD_BYTES)}.`;
    case "duplicate":
      return "Ya estaba en la lista.";
    case "limit_reached":
      return maxFiles === 1 ? "Esta herramienta trabaja con un archivo a la vez." : `Caben hasta ${maxFiles} archivos a la vez.`;
  }
}

export function rejectionToast(rejections: readonly FileRejection[], context: RejectionContext): ToastInput {
  const [first] = rejections;
  const title =
    rejections.length === 1 && first ? `«${first.fileName}» no se añadió` : `${rejections.length} archivos no se añadieron`;
  const reasons = [...new Set(rejections.map((rejection) => rejectionReasonCopy(rejection.reason, context)))];

  return { tone: "warning", title, description: reasons.join(" ") };
}

export function uploadHint(accept: FileAccept, maxFiles: number): string {
  const formats = [...new Set(accept.extensions.map((extension) => extension.slice(1).toUpperCase()))].join(", ");
  const size = formatBytes(MAX_UPLOAD_BYTES);
  return maxFiles === 1 ? `${formats} · hasta ${size}` : `${formats} · hasta ${maxFiles} archivos de ${size}`;
}

// ——— Resultados ———

export function successToast(download: FileDownload, detail?: string | null): ToastInput {
  const saved = `Guardamos «${download.filename}» en tus descargas.`;
  return { tone: "success", title: "Listo", description: detail ? `${detail} ${saved}` : saved };
}

export function plural(count: number, singular: string, pluralForm: string): string {
  return `${count} ${count === 1 ? singular : pluralForm}`;
}

export function compressionSummary({ originalBytes, resultBytes }: FileDownload): string | null {
  if (originalBytes === null || resultBytes === null || originalBytes === 0) return null;
  if (resultBytes >= originalBytes) return "Ya estaba bien optimizado, así que lo dejamos igual.";
  const savedPercent = Math.round((1 - resultBytes / originalBytes) * 100);
  return `Pasó de ${formatBytes(originalBytes)} a ${formatBytes(resultBytes)} (−${savedPercent} %).`;
}

export function zipSummary(noun: { singular: string; plural: string }) {
  return ({ resultCount }: FileDownload): string | null =>
    resultCount && resultCount > 1 ? `${plural(resultCount, noun.singular, noun.plural)}, juntos en un ZIP.` : null;
}

export function redactionSummary({ resultCount }: FileDownload): string | null {
  return resultCount ? `Censuramos ${plural(resultCount, "coincidencia", "coincidencias")}.` : null;
}

export function ocrSummary({ resultCount }: FileDownload): string | null {
  return resultCount ? `Reconocimos texto en ${plural(resultCount, "página", "páginas")}.` : null;
}

export function apiErrorToast(error: ApiError, failureTitle: string): ToastInput {
  switch (error.kind) {
    case "aborted":
      return { tone: "info", title: "Cancelado", description: "Tus archivos siguen aquí." };
    case "rate_limited":
      return {
        tone: "warning",
        title: "Vas muy rápido",
        description: error.retryAfterSeconds
          ? `Espera ${error.retryAfterSeconds} s y vuelve a intentarlo.`
          : API_ERROR_COPY.rate_limited,
      };
    default:
      return { tone: "error", title: failureTitle, description: error.message };
  }
}

// ——— Qué falta para poder ejecutar ———

export function multiFileBlocker(fileCount: number, minFiles: number, isEngineOffline: boolean): string | null {
  if (fileCount === 0) return minFiles > 1 ? `Añade al menos ${minFiles} archivos para empezar.` : "Añade archivos para empezar.";
  if (fileCount < minFiles) return "Añade un archivo más para continuar.";
  if (isEngineOffline) return ENGINE_OFFLINE_COPY;
  return null;
}

interface FileToolState {
  hasFile: boolean;
  isEngineOffline: boolean;
  missingEngine: EngineId | null;
  fieldError: string | null;
}

export function fileToolBlocker({ hasFile, isEngineOffline, missingEngine, fieldError }: FileToolState): string | null {
  if (missingEngine) return ENGINE_COPY[missingEngine].missing;
  if (!hasFile) return "Elige un archivo para empezar.";
  if (fieldError) return fieldError;
  if (isEngineOffline) return ENGINE_OFFLINE_COPY;
  return null;
}

// ——— Editor de páginas ———

export const PAGE_EDITOR_HINT: Record<PageEditorMode, string> = {
  organize: "Arrastra las páginas para ordenarlas. Usa los botones para girarlas o quitarlas.",
  rotate: "Toca una página para girarla 90°.",
  delete: "Toca las páginas que quieras eliminar.",
  extract: "Toca las páginas que quieras extraer.",
};

export interface PageCounts {
  total: number;
  kept: number;
  rotated: number;
  selected: number;
}

export function pageEditorBlocker(mode: PageEditorMode, counts: PageCounts, isEngineOffline: boolean): string | null {
  if (isEngineOffline) return ENGINE_OFFLINE_COPY;
  switch (mode) {
    case "organize":
      return counts.kept === 0 ? "Deja al menos una página." : null;
    case "rotate":
      return counts.rotated === 0 ? "Gira al menos una página para continuar." : null;
    case "delete":
      if (counts.kept === counts.total) return "Toca las páginas que quieras eliminar.";
      return counts.kept === 0 ? "No puedes eliminar todas las páginas." : null;
    case "extract":
      return counts.selected === 0 ? "Toca las páginas que quieras extraer." : null;
  }
}

export function pageEditorSummary(mode: PageEditorMode, counts: PageCounts): string {
  switch (mode) {
    case "organize":
      return `El PDF tendrá ${plural(counts.kept, "página", "páginas")}.`;
    case "rotate":
      return `${plural(counts.rotated, "página girada", "páginas giradas")} de ${counts.total}.`;
    case "delete":
      return `Se eliminarán ${plural(counts.total - counts.kept, "página", "páginas")}.`;
    case "extract":
      return `${plural(counts.selected, "página elegida", "páginas elegidas")} de ${counts.total}.`;
  }
}

// ——— Formularios ———

export const FORM_COPY = {
  loading: "Leyendo el formulario…",
  empty: "Este PDF no tiene campos rellenables. Prueba con otro documento.",
  flattenLabel: "Aplanar el formulario",
    flattenDescription: "Convierte los campos en contenido fijo: ya no podrás editarlos en el PDF descargado. Déjalo desactivado para conservar la edición.",
  noEditableFields: "Todos los campos de este formulario son de solo lectura.",
} as const;
