import { useCallback, useEffect, useRef, useState } from "react";

import { downloadBlob } from "../lib/download";
import { ApiError, type FileDownload } from "../services/apiClient";

export type JobOutcome = { ok: true; download: FileDownload } | { ok: false; error: ApiError };

/** Ejecuta una herramienta, descarga el resultado y expone carga/cancelación. Común a todas. */
export function useToolJob() {
  const [isRunning, setIsRunning] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);

  // Si la vista desaparece a mitad de proceso, cortamos la petición.
  useEffect(() => () => controllerRef.current?.abort(), []);

  const run = useCallback(async (task: (signal: AbortSignal) => Promise<FileDownload>): Promise<JobOutcome> => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    setIsRunning(true);

    try {
      const download = await task(controller.signal);
      downloadBlob(download.blob, download.filename);
      return { ok: true, download };
    } catch (error) {
      return { ok: false, error: error instanceof ApiError ? error : new ApiError("server") };
    } finally {
      // Solo la petición vigente puede apagar el estado de carga.
      if (controllerRef.current === controller) {
        controllerRef.current = null;
        setIsRunning(false);
      }
    }
  }, []);

  const cancel = useCallback(() => controllerRef.current?.abort(), []);

  return { isRunning, run, cancel };
}
