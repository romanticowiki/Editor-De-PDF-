import { cx } from "../../lib/cx";

interface SpinnerProps {
  className?: string;
}

/** Decorativo: el estado de carga siempre se comunica también con texto. */
export function Spinner({ className }: SpinnerProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden
      className={cx("motion-safe:animate-spin motion-safe:[animation-duration:0.9s]", className)}
    >
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.25" strokeWidth="2.5" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}
