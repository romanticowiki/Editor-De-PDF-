import type { ComponentPropsWithRef } from "react";

import { cx } from "../../lib/cx";

interface IconButtonProps extends ComponentPropsWithRef<"button"> {
  /** Obligatorio: un botón solo-icono sin nombre es invisible para lectores de pantalla. */
  label: string;
  round?: boolean;
}

export function IconButton({ label, round = false, className, children, ...rest }: IconButtonProps) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      {...rest}
      className={cx(
        // after:-inset-1 amplía el área táctil sin cambiar el tamaño visual.
        "relative inline-flex size-9 shrink-0 items-center justify-center text-muted touch-manipulation transition-[background-color,color,transform,opacity] duration-150 ease-out-quart after:absolute after:-inset-1 after:content-[''] hover:bg-ink/6 hover:text-ink active:scale-[0.92] disabled:pointer-events-none disabled:opacity-35",
        round ? "rounded-full" : "rounded-[0.625rem]",
        className,
      )}
    >
      {children}
    </button>
  );
}
