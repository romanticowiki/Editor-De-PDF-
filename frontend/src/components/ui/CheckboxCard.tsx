import { Check } from "lucide-react";

import { CHOICE_CARD } from "./inputStyles";

interface CheckboxCardProps {
  label: string;
  description?: string | undefined;
  checked: boolean;
  disabled?: boolean;
  onChange: (checked: boolean) => void;
}

export function CheckboxCard({ label, description, checked, disabled = false, onChange }: CheckboxCardProps) {
  return (
    <label className={CHOICE_CARD}>
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
        className="peer sr-only"
      />
      <span
        aria-hidden
        className="mt-0.5 flex size-[1.125rem] shrink-0 items-center justify-center rounded-[0.3rem] border-[1.5px] border-subtle text-on-accent transition-colors duration-150 peer-checked:border-accent peer-checked:bg-accent [&>svg]:scale-0 peer-checked:[&>svg]:scale-100"
      >
        <Check className="size-3 transition-transform duration-200 ease-out-quart" />
      </span>
      <span className="flex flex-col gap-0.5">
        <span className="text-[0.9375rem] font-semibold text-ink">{label}</span>
        {description && <span className="text-[0.8125rem] leading-snug text-muted">{description}</span>}
      </span>
    </label>
  );
}
