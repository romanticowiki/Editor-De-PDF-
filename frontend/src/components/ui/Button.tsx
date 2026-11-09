import type { ComponentPropsWithRef, ReactNode } from "react";

import { cx } from "../../lib/cx";
import { Spinner } from "./Spinner";

type ButtonVariant = "primary" | "quiet";

const BASE =
  "inline-flex h-11 select-none items-center justify-center gap-2 rounded-control px-5 text-[0.9375rem] font-semibold tracking-[-0.01em] whitespace-nowrap touch-manipulation transition-[background-color,color,transform,opacity] duration-150 ease-out-quart active:scale-[0.97] disabled:pointer-events-none disabled:opacity-45";

const VARIANTS: Record<ButtonVariant, string> = {
  primary:
    "bg-accent text-on-accent shadow-[inset_0_1px_0_rgb(255_255_255/0.2),0_8px_18px_-10px_var(--accent)] hover:bg-accent-hover",
  quiet: "text-ink-soft hover:bg-ink/6 hover:text-ink",
};

interface ButtonProps extends ComponentPropsWithRef<"button"> {
  variant?: ButtonVariant;
  isLoading?: boolean;
  icon?: ReactNode;
}

export function Button({ variant = "primary", isLoading = false, icon, disabled, className, children, ...rest }: ButtonProps) {
  return (
    <button
      type="button"
      {...rest}
      disabled={disabled || isLoading}
      aria-busy={isLoading || undefined}
      className={cx(BASE, VARIANTS[variant], className)}
    >
      {isLoading ? <Spinner className="size-[1.125rem]" /> : icon}
      <span>{children}</span>
    </button>
  );
}
