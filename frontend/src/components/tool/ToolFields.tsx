import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";

import { type FieldValues, excludedOption, fieldError, isFieldVisible } from "../../lib/fields";
import { exitTransition, springs } from "../../lib/motion";
import type { ToolField } from "../../tools/types";
import { CheckboxCard } from "../ui/CheckboxCard";
import { ChoiceCards } from "../ui/ChoiceCards";
import { TextFieldInput } from "../ui/TextFieldInput";

interface ToolFieldsProps {
  fields: readonly ToolField[];
  values: FieldValues;
  disabled: boolean;
  onChange: (name: string, value: string) => void;
}

/** Opciones de una herramienta, generadas desde el catálogo. Los campos condicionales aparecen con suavidad. */
export function ToolFields({ fields, values, disabled, onChange }: ToolFieldsProps) {
  const [touched, setTouched] = useState<ReadonlySet<string>>(() => new Set());

  const markTouched = (name: string) => {
    setTouched((current) => (current.has(name) ? current : new Set(current).add(name)));
  };

  return (
    <AnimatePresence initial={false}>
      {fields
        .filter((field) => isFieldVisible(field, values))
        .map((field) => (
          <motion.div
            key={field.name}
            layout="position"
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, transition: exitTransition }}
            transition={springs.snappy}
          >
            {field.kind === "choice" ? (
              <ChoiceCards
                field={field}
                value={values[field.name] ?? field.defaultValue}
                disabled={disabled}
                excludeValue={excludedOption(field, values)}
                onChange={(value) => onChange(field.name, value)}
              />
            ) : field.kind === "text" ? (
              <TextFieldInput
                field={field}
                value={values[field.name] ?? ""}
                error={touched.has(field.name) ? fieldError(field, values[field.name] ?? "") : null}
                disabled={disabled}
                onChange={(value) => onChange(field.name, value)}
                onBlur={() => markTouched(field.name)}
              />
            ) : (
              <CheckboxCard
                label={field.label}
                description={field.description}
                checked={(values[field.name] ?? field.defaultValue) === "true"}
                disabled={disabled}
                onChange={(checked) => onChange(field.name, String(checked))}
              />
            )}
          </motion.div>
        ))}
    </AnimatePresence>
  );
}
