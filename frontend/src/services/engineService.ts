import { isRecord } from "../lib/guards";
import { requestJson } from "./apiClient";

export type EngineId = "office" | "ocr" | "translate";

const ENGINE_IDS: readonly EngineId[] = ["office", "ocr", "translate"];

/** Solo contiene los motores que el backend ya informó; ausente = aún no lo sabemos. */
export type EngineAvailability = Partial<Record<EngineId, boolean>>;

const ENGINES_TIMEOUT_MS = 4_000;

export function fetchEngineAvailability(signal?: AbortSignal): Promise<EngineAvailability> {
  return requestJson("/tools", parseEngineAvailability, { signal, timeoutMs: ENGINES_TIMEOUT_MS });
}

function parseEngineAvailability(data: unknown): EngineAvailability {
  const engines = isRecord(data) && isRecord(data.engines) ? data.engines : {};
  const availability: EngineAvailability = {};
  for (const id of ENGINE_IDS) {
    const engine = engines[id];
    if (isRecord(engine) && typeof engine.available === "boolean") availability[id] = engine.available;
  }
  return availability;
}
