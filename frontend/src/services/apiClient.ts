/**
 * Único punto de salida HTTP. Traduce cualquier fallo (red, timeout, 429, 4xx, 5xx)
 * a un `ApiError` tipado con un mensaje ya apto para la persona usuaria.
 */

import { API_ERROR_COPY } from "../copy/messages";
import { env } from "../config/env";
import { isRecord } from "../lib/guards";

export type ApiErrorKind = "network" | "timeout" | "aborted" | "rate_limited" | "client" | "server";

interface ApiErrorDetails {
  status?: number;
  retryAfterSeconds?: number | null;
}

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | null;
  readonly retryAfterSeconds: number | null;

  constructor(kind: ApiErrorKind, message: string = API_ERROR_COPY[kind], details: ApiErrorDetails = {}) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = details.status ?? null;
    this.retryAfterSeconds = details.retryAfterSeconds ?? null;
  }
}

export interface RequestOptions {
  method?: "GET" | "POST";
  body?: BodyInit;
  signal?: AbortSignal | undefined;
  timeoutMs?: number;
}

export interface FileDownload {
  blob: Blob;
  filename: string;
  /** Tamaños antes/después cuando la herramienta los informa (p. ej. Comprimir). */
  originalBytes: number | null;
  resultBytes: number | null;
  /** Cantidad que informa la herramienta: archivos en el ZIP, coincidencias censuradas… */
  resultCount: number | null;
}

const DEFAULT_TIMEOUT_MS = 15_000;

export function requestJson<T>(path: string, parse: (data: unknown) => T, options: RequestOptions = {}): Promise<T> {
  return execute(path, options, async (response) => parse(await response.json()));
}

export function requestFile(path: string, fallbackFilename: string, options: RequestOptions = {}): Promise<FileDownload> {
  return execute(path, options, async (response) => ({
    blob: await response.blob(),
    filename: filenameFromDisposition(response.headers.get("Content-Disposition")) ?? fallbackFilename,
    originalBytes: parseSize(response.headers.get("X-Original-Size")),
    resultBytes: parseSize(response.headers.get("X-Result-Size")),
    resultCount: parseSize(response.headers.get("X-Result-Count")),
  }));
}

async function execute<T>(path: string, options: RequestOptions, read: (response: Response) => Promise<T>): Promise<T> {
  const { method = "GET", body, signal, timeoutMs = DEFAULT_TIMEOUT_MS } = options;
  const timeoutSignal = AbortSignal.timeout(timeoutMs);
  const combinedSignal = signal ? AbortSignal.any([signal, timeoutSignal]) : timeoutSignal;

  try {
    const response = await fetch(`${env.apiBaseUrl}${path}`, {
      method,
      body: body ?? null,
      signal: combinedSignal,
      credentials: "omit", // la API no usa cookies: no enviamos ninguna
      cache: "no-store",
      referrerPolicy: "no-referrer",
    });
    if (!response.ok) throw await toApiError(response);
    // El timeout también cubre la lectura del cuerpo, no solo las cabeceras.
    return await read(response);
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (signal?.aborted) throw new ApiError("aborted");
    if (timeoutSignal.aborted) throw new ApiError("timeout");
    if (error instanceof SyntaxError) throw new ApiError("server");
    throw new ApiError("network");
  }
}

async function toApiError(response: Response): Promise<ApiError> {
  const { status } = response;

  if (status >= 500) {
    // 503 (falta un programa) y 504 (tiempo agotado) traen un mensaje pensado para la persona;
    // cualquier otro 5xx se oculta para no filtrar detalles internos.
    const detail = status === 503 || status === 504 ? await readDetail(response) : null;
    return new ApiError(status === 504 ? "timeout" : "server", detail ?? undefined, { status });
  }

  const detail = await readDetail(response);
  if (status === 429) {
    const retryAfterSeconds = parseRetryAfter(response.headers.get("Retry-After"));
    return new ApiError("rate_limited", detail ?? undefined, { status, retryAfterSeconds });
  }
  return new ApiError("client", detail ?? undefined, { status });
}

async function readDetail(response: Response): Promise<string | null> {
  try {
    const data: unknown = await response.json();
    // FastAPI devuelve `detail` como array en errores de validación: usamos el copy genérico.
    return isRecord(data) && typeof data.detail === "string" ? data.detail : null;
  } catch {
    return null;
  }
}

export function parseRetryAfter(value: string | null): number | null {
  if (!value) return null;
  const seconds = Number(value);
  return Number.isFinite(seconds) && seconds >= 0 ? Math.ceil(seconds) : null;
}

function parseSize(value: string | null): number | null {
  const bytes = Number(value);
  return value !== null && Number.isSafeInteger(bytes) && bytes >= 0 ? bytes : null;
}

export function filenameFromDisposition(header: string | null): string | null {
  if (!header) return null;

  // `filename*` (RFC 5987) conserva tildes y eñes: tiene prioridad sobre el `filename` ASCII.
  const encoded = /filename\*\s*=\s*UTF-8''([^;]+)/i.exec(header)?.[1];
  if (encoded) {
    try {
      return decodeURIComponent(encoded.trim());
    } catch {
      // Codificación inválida: seguimos con el nombre ASCII.
    }
  }
  return /filename\s*=\s*"?([^";]+)"?/i.exec(header)?.[1]?.trim() || null;
}
