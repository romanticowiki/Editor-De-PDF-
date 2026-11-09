export const FIELD_LABEL = "text-[0.8125rem] font-semibold tracking-[0.01em] text-ink-soft";

export const FIELD_INPUT =
  "w-full rounded-control border border-line/70 bg-surface px-3.5 py-2.5 text-base text-ink transition-[border-color] duration-150 ease-out-quart placeholder:text-muted/70 hover:border-subtle focus-visible:border-accent-ring aria-invalid:border-danger disabled:cursor-not-allowed disabled:opacity-60";

// `relative`: el input oculto (sr-only es absoluto) queda dentro de la tarjeta; si no, dentro de un panel
// con scroll se posicionaría respecto a la página y la haría crecer.
export const CHOICE_CARD =
  "relative flex cursor-pointer items-start gap-3 rounded-control border border-line/70 bg-surface p-3.5 transition-[background-color,border-color] duration-150 ease-out-quart hover:border-subtle has-checked:border-accent-ring has-checked:bg-accent-soft/60 has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-accent-ring has-disabled:cursor-not-allowed has-disabled:opacity-60";
