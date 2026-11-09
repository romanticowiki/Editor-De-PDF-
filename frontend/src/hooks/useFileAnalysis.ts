import { useEffect, useState } from "react";

import { ApiError } from "../services/apiClient";

export type AnalysisState<T> =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; data: T }
  | { status: "error"; error: ApiError };

/**
 * Pide al motor local información de un archivo (miniaturas, campos de formulario…).
 * Cambiar de archivo o salir de la vista cancela la petición en curso.
 * `analyze` debe ser una referencia estable (función de módulo).
 */
export function useFileAnalysis<T>(
  file: File | null,
  analyze: (file: File, signal: AbortSignal) => Promise<T>,
): AnalysisState<T> {
  const [state, setState] = useState<AnalysisState<T>>({ status: "idle" });

  useEffect(() => {
    if (!file) {
      setState({ status: "idle" });
      return;
    }

    const controller = new AbortController();
    setState({ status: "loading" });
    analyze(file, controller.signal).then(
      (data) => {
        if (!controller.signal.aborted) setState({ status: "ready", data });
      },
      (error: unknown) => {
        if (controller.signal.aborted) return;
        setState({ status: "error", error: error instanceof ApiError ? error : new ApiError("server") });
      },
    );
    return () => controller.abort();
  }, [file, analyze]);

  return state;
}
