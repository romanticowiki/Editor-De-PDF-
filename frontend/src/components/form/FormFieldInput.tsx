import { useId } from "react";

import type { FormFieldInfo, FormValue } from "../../services/formsService";
import { CheckboxCard } from "../ui/CheckboxCard";
import { FIELD_INPUT, FIELD_LABEL } from "../ui/inputStyles";

interface FormFieldInputProps {
  field: FormFieldInfo;
  value: FormValue | undefined;
  disabled: boolean;
  onChange: (value: FormValue) => void;
}

const READ_ONLY_NOTE = "Solo lectura";

export function FormFieldInput({ field, value, disabled, onChange }: FormFieldInputProps) {
  const id = useId();
  const isDisabled = disabled || field.readOnly;
  const text = typeof value === "string" ? value : "";

  const label = (
    <label htmlFor={id} className={FIELD_LABEL}>
      {field.label}
      {field.readOnly && <span className="font-normal text-muted"> · {READ_ONLY_NOTE}</span>}
    </label>
  );

  switch (field.kind) {
    case "checkbox":
      return (
        <CheckboxCard
          label={field.label}
          description={field.readOnly ? READ_ONLY_NOTE : undefined}
          checked={value === true}
          disabled={isDisabled}
          onChange={onChange}
        />
      );

    case "choice":
      return (
        <div className="flex flex-col gap-2">
          {label}
          <select id={id} value={text} disabled={isDisabled} onChange={(event) => onChange(event.target.value)} className={FIELD_INPUT}>
            <option value="">Sin elegir</option>
            {field.options.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </div>
      );

    case "radio":
      return (
        <fieldset disabled={isDisabled} className="flex flex-col gap-2 md:col-span-2">
          <legend className={`mb-2 ${FIELD_LABEL}`}>{field.label}</legend>
          <div className="flex flex-wrap gap-2">
            {field.options.map((option) => (
              <label
                key={option}
                className="relative cursor-pointer rounded-full border border-line/70 bg-surface px-3.5 py-2 text-sm font-semibold text-ink transition-[background-color,border-color] duration-150 ease-out-quart hover:border-subtle has-checked:border-accent-ring has-checked:bg-accent-soft/60 has-focus-visible:outline-2 has-focus-visible:outline-offset-2 has-focus-visible:outline-accent-ring"
              >
                <input
                  type="radio"
                  name={id}
                  value={option}
                  checked={text === option}
                  onChange={() => onChange(option)}
                  className="sr-only"
                />
                {option}
              </label>
            ))}
          </div>
        </fieldset>
      );

    case "text":
      return (
        <div className={field.multiline ? "flex flex-col gap-2 md:col-span-2" : "flex flex-col gap-2"}>
          {label}
          {field.multiline ? (
            <textarea
              id={id}
              value={text}
              rows={3}
              disabled={isDisabled}
              maxLength={field.maxLength ?? undefined}
              onChange={(event) => onChange(event.target.value)}
              className={`${FIELD_INPUT} min-h-20 resize-y`}
            />
          ) : (
            <input
              id={id}
              type="text"
              value={text}
              disabled={isDisabled}
              maxLength={field.maxLength ?? undefined}
              autoComplete="off"
              onChange={(event) => onChange(event.target.value)}
              className={FIELD_INPUT}
            />
          )}
        </div>
      );
  }
}
