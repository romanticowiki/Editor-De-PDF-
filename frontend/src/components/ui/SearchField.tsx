import { Search } from "lucide-react";
import type { Ref } from "react";

import { cx } from "../../lib/cx";

interface SearchFieldProps {
  value: string;
  onChange: (value: string) => void;
  /** "plain" dentro de superficies translúcidas: nunca apilamos vidrio sobre vidrio. */
  variant?: "glass" | "plain";
  inputRef?: Ref<HTMLInputElement>;
  className?: string;
}

export function SearchField({ value, onChange, variant = "glass", inputRef, className }: SearchFieldProps) {
  return (
    <label
      className={cx(
        "flex h-12 w-full items-center gap-3 rounded-full px-5 has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-accent-ring",
        variant === "glass" ? "glass [--glass-alpha:0.72]" : "border border-line/70 bg-surface-sunken",
        className,
      )}
    >
      <Search className="size-[1.125rem] text-muted" aria-hidden />
      <input
        ref={inputRef}
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Buscar: Word, comprimir, Excel…"
        aria-label="Buscar herramienta"
        autoComplete="off"
        spellCheck={false}
        className="h-full min-w-0 flex-1 bg-transparent text-base text-ink outline-none placeholder:text-muted focus-visible:outline-none"
      />
    </label>
  );
}
