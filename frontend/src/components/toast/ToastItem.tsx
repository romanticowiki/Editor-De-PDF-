import { CircleAlert, CircleCheck, Info, type LucideIcon, TriangleAlert, X } from "lucide-react";
import { motion } from "motion/react";

import { exitTransition, springs } from "../../lib/motion";
import { IconButton } from "../ui/IconButton";
import type { ToastRecord, ToastTone } from "./types";

const TONE_ICON: Record<ToastTone, { Icon: LucideIcon; className: string }> = {
  info: { Icon: Info, className: "text-muted" },
  success: { Icon: CircleCheck, className: "text-success" },
  warning: { Icon: TriangleAlert, className: "text-warning" },
  error: { Icon: CircleAlert, className: "text-danger" },
};

interface ToastItemProps {
  toast: ToastRecord;
  onDismiss: (id: string) => void;
}

export function ToastItem({ toast, onDismiss }: ToastItemProps) {
  const { Icon, className } = TONE_ICON[toast.tone];

  return (
    <motion.div
      layout
      role={toast.tone === "error" ? "alert" : "status"}
      initial={{ opacity: 0, y: 16, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 8, scale: 0.98, transition: exitTransition }}
      transition={springs.snappy}
      className="glass pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-panel py-3 pr-2 pl-4 [--glass-alpha:0.94]"
    >
      <Icon className={`mt-0.5 size-5 ${className}`} aria-hidden />
      <div className="flex min-w-0 flex-1 flex-col gap-0.5 py-px">
        <p className="text-[0.9375rem] leading-snug font-semibold tracking-[-0.01em] text-ink">{toast.title}</p>
        {toast.description && <p className="text-sm leading-relaxed text-muted">{toast.description}</p>}
      </div>
      <IconButton label="Cerrar aviso" onClick={() => onDismiss(toast.id)} className="-my-1">
        <X className="size-4" aria-hidden />
      </IconButton>
    </motion.div>
  );
}
