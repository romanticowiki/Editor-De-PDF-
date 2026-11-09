export type ToastTone = "info" | "success" | "warning" | "error";

export interface ToastInput {
  tone?: ToastTone;
  title: string;
  description?: string;
  durationMs?: number;
}

export interface ToastRecord {
  id: string;
  tone: ToastTone;
  title: string;
  description?: string | undefined;
}

export interface ToastApi {
  notify: (toast: ToastInput) => void;
  dismiss: (id: string) => void;
}
