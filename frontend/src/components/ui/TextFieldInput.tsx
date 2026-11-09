import { useId } from "react";

import { cx } from "../../lib/cx";
import type { TextField } from "../../tools/types";
import { FIELD_INPUT, FIELD_LABEL } from "./inputStyles";

interface TextFieldInputProps {
  field: TextField;
  value: string;
  /** Solo se pasa tras salir del campo: no reñimos mientras la persona aún escribe. */
  error: string | null;
  disabled: boolean;
  onChange: (value: string) => void;
  onBlur: () => void;
}

export function TextFieldInput({ field, value, error, disabled, onChange, onBlur }: TextFieldInputProps) {
  const id = useId();
  const noteId = `${id}-nota`;
  const note = error ?? field.hint;

  const shared = {
    id,
    value,
    disabled,
    maxLength: field.maxLength,
    placeholder: field.placeholder,
    onBlur,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": note ? noteId : undefined,
  };

  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={id} className={FIELD_LABEL}>
        {field.label}
      </label>
      {field.multiline ? (
        <textarea
          {...shared}
          rows={4}
          onChange={(event) => onChange(event.target.value)}
          className={cx(FIELD_INPUT, "min-h-24 resize-y leading-relaxed")}
        />
      ) : (
        <input
          {...shared}
          type="text"
          inputMode={field.numeric ? "numeric" : undefined}
          autoComplete="off"
          onChange={(event) => onChange(event.target.value)}
          className={FIELD_INPUT}
        />
      )}
      {note && (
        <p id={noteId} className={cx("text-[0.8125rem] leading-snug", error ? "text-danger" : "text-muted")}>
          {note}
        </p>
      )}
    </div>
  );
}
