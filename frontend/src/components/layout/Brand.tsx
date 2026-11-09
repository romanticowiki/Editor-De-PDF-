import { Layers } from "lucide-react";

export function Brand() {
  return (
    <a href="#/" className="flex items-center gap-2.5 rounded-control" aria-label="EPDF, inicio">
      <span className="flex size-9 items-center justify-center rounded-[0.75rem] bg-ink text-surface shadow-lift">
        <Layers className="size-[1.125rem]" aria-hidden />
      </span>
      <span className="text-[1.0625rem] font-bold tracking-[-0.02em] text-ink">EPDF</span>
    </a>
  );
}
