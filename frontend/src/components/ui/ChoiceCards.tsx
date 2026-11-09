import { useId } from "react";

import type { ChoiceField } from "../../tools/types";
import { CHOICE_CARD, FIELD_LABEL } from "./inputStyles";

interface ChoiceCardsProps {
  field: ChoiceField;
  value: string;
  disabled?: boolean;
  /** Opción que no se muestra porque la ocupa otro campo (idioma origen ≠ destino). */
  excludeValue?: string;
  onChange: (value: string) => void;
}

/** Grupo de opciones con radios nativos: flechas del teclado y lectores de pantalla funcionan solos. */
export function ChoiceCards({ field, value, disabled = false, excludeValue, onChange }: ChoiceCardsProps) {
  const groupName = useId();
  const options = field.options.filter((option) => option.value !== excludeValue);

  return (
    <fieldset disabled={disabled} className="flex flex-col gap-2">
      <legend className={`mb-2 ${FIELD_LABEL}`}>{field.label}</legend>
      {options.map((option) => (
        <label key={option.value} className={CHOICE_CARD}>
          <input
            type="radio"
            name={groupName}
            value={option.value}
            checked={value === option.value}
            onChange={() => onChange(option.value)}
            className="peer sr-only"
          />
          <span
            aria-hidden
            className="mt-0.5 flex size-[1.125rem] shrink-0 items-center justify-center rounded-full border-[1.5px] border-subtle transition-colors duration-150 peer-checked:border-accent [&>span]:scale-0 peer-checked:[&>span]:scale-100"
          >
            <span className="size-2 rounded-full bg-accent transition-transform duration-200 ease-out-quart" />
          </span>
          <span className="flex flex-col gap-0.5">
            <span className="text-[0.9375rem] font-semibold text-ink">{option.label}</span>
            {option.description && <span className="text-[0.8125rem] leading-snug text-muted">{option.description}</span>}
          </span>
        </label>
      ))}
    </fieldset>
  );
}
