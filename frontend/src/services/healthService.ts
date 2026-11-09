import { isRecord } from "../lib/guards";
import { ApiError, requestJson } from "./apiClient";

export interface HealthStatus {
  appName: string;
  version: string;
  uptimeSeconds: number;
}

const HEALTH_TIMEOUT_MS = 4_000;

export function fetchHealth(signal?: AbortSignal): Promise<HealthStatus> {
  return requestJson("/health", parseHealth, { signal, timeoutMs: HEALTH_TIMEOUT_MS });
}

// Validación en tiempo de ejecución: no confiamos en la forma de la respuesta.
function parseHealth(data: unknown): HealthStatus {
  if (
    !isRecord(data) ||
    data.status !== "ok" ||
    typeof data.app_name !== "string" ||
    typeof data.version !== "string" ||
    typeof data.uptime_seconds !== "number"
  ) {
    throw new ApiError("server");
  }
  return { appName: data.app_name, version: data.version, uptimeSeconds: data.uptime_seconds };
}
