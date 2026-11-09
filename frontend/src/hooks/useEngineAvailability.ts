import { useEffect, useState } from "react";

import { type EngineAvailability, fetchEngineAvailability } from "../services/engineService";
import type { ApiHealth } from "./useApiHealth";

// Instalar Office o los datos del OCR no apaga el motor: hay que volver a preguntar de vez en cuando.
const REFRESH_MS = 60_000;

export function useEngineAvailability(apiHealth: ApiHealth): EngineAvailability {
  const [availability, setAvailability] = useState<EngineAvailability>({});

  useEffect(() => {
    if (apiHealth !== "online") return;

    let controller: AbortController | undefined;
    const refresh = () => {
      controller?.abort();
      controller = new AbortController();
      fetchEngineAvailability(controller.signal)
        .then(setAvailability)
        .catch(() => {
          // Sin datos no bloqueamos nada: si falta un programa, el backend lo explicará al usar la herramienta.
        });
    };

    refresh();
    // Al volver a la ventana (p. ej. tras instalar algo) el estado se actualiza al momento.
    window.addEventListener("focus", refresh);
    const interval = window.setInterval(refresh, REFRESH_MS);
    return () => {
      controller?.abort();
      window.removeEventListener("focus", refresh);
      window.clearInterval(interval);
    };
  }, [apiHealth]);

  return availability;
}
