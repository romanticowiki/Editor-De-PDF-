import { createContext, use } from "react";

import type { ToastApi } from "./types";

export const ToastContext = createContext<ToastApi | null>(null);

export function useToast(): ToastApi {
  const api = use(ToastContext);
  if (!api) throw new Error("useToast debe usarse dentro de <ToastProvider>.");
  return api;
}
