import { AnimatePresence } from "motion/react";
import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ToastContext } from "./toastContext";
import { ToastItem } from "./ToastItem";
import type { ToastApi, ToastInput, ToastRecord, ToastTone } from "./types";

const MAX_VISIBLE = 3;

// Los avisos que piden actuar se quedan más tiempo en pantalla.
const DURATION_MS: Record<ToastTone, number> = {
  info: 4_000,
  success: 4_500,
  warning: 6_500,
  error: 7_500,
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastRecord[]>([]);
  const timers = useRef(new Map<string, number>());

  const dismiss = useCallback((id: string) => {
    const timer = timers.current.get(id);
    if (timer !== undefined) {
      window.clearTimeout(timer);
      timers.current.delete(id);
    }
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const notify = useCallback(
    ({ tone = "info", title, description, durationMs }: ToastInput) => {
      const id = crypto.randomUUID();
      setToasts((current) => [...current, { id, tone, title, description }].slice(-MAX_VISIBLE));
      timers.current.set(id, window.setTimeout(() => dismiss(id), durationMs ?? DURATION_MS[tone]));
    },
    [dismiss],
  );

  useEffect(() => {
    const pending = timers.current;
    return () => {
      pending.forEach((timer) => window.clearTimeout(timer));
      pending.clear();
    };
  }, []);

  const api = useMemo<ToastApi>(() => ({ notify, dismiss }), [notify, dismiss]);

  return (
    <ToastContext value={api}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex flex-col items-center gap-2 px-4 pb-[max(1.5rem,env(safe-area-inset-bottom))]"
      >
        <AnimatePresence initial={false} mode="popLayout">
          {toasts.map((toast) => (
            <ToastItem key={toast.id} toast={toast} onDismiss={dismiss} />
          ))}
        </AnimatePresence>
      </div>
    </ToastContext>
  );
}
