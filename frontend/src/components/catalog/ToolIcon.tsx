import type { LucideIcon } from "lucide-react";

import { cx } from "../../lib/cx";
import type { ToolTone } from "../../tools/types";

const TONE_CLASSES: Record<ToolTone, string> = {
  accent: "bg-accent-soft text-accent",
  success: "bg-success-soft text-success",
  warning: "bg-warning-soft text-warning",
  danger: "bg-danger-soft text-danger",
  teal: "bg-teal-soft text-teal",
  ink: "bg-ink text-surface",
};

interface ToolIconProps {
  icon: LucideIcon;
  tone: ToolTone;
  size?: "md" | "lg";
}

export function ToolIcon({ icon: Icon, tone, size = "md" }: ToolIconProps) {
  return (
    <span
      className={cx(
        "flex shrink-0 items-center justify-center",
        size === "lg" ? "size-14 rounded-[1.125rem]" : "size-10 rounded-[0.75rem]",
        TONE_CLASSES[tone],
      )}
    >
      <Icon className={size === "lg" ? "size-7" : "size-5"} aria-hidden />
    </span>
  );
}
