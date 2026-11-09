import type { ToolField } from "../tools/types";

export type FieldValues = Readonly<Record<string, string>>;

const REQUIRED_MESSAGE = "Completa este campo para continuar.";

export function initialFieldValues(fields: readonly ToolField[] = []): Record<string, string> {
  return Object.fromEntries(fields.map((field) => [field.name, field.defaultValue]));
}

/** Aplica un cambio y reconcilia los campos que deben diferir de otro (`distinctFrom`).
 *  Si el nuevo valor hace que un campo choque con su contraparte, ese campo salta a la
 *  primera opción distinta. Así origen y destino nunca coinciden. */
export function applyFieldChange(
  fields: readonly ToolField[],
  values: FieldValues,
  name: string,
  value: string,
): Record<string, string> {
  const next: Record<string, string> = { ...values, [name]: value };
  for (const field of fields) {
    if (field.kind !== "choice" || !field.distinctFrom) continue;
    const counterpart = field.distinctFrom;
    if (next[field.name] !== next[counterpart]) continue;
    const alternative = field.options.find((option) => option.value !== next[counterpart]);
    if (alternative) next[field.name] = alternative.value;
  }
  return next;
}

/** Valor que este campo no puede ofrecer porque lo ocupa su contraparte `distinctFrom`. */
export function excludedOption(field: ToolField, values: FieldValues): string | undefined {
  return field.kind === "choice" && field.distinctFrom ? values[field.distinctFrom] : undefined;
}

export function isFieldVisible(field: ToolField, values: FieldValues): boolean {
  return !field.visibleWhen || values[field.visibleWhen.field] === field.visibleWhen.equals;
}

export function fieldError(field: ToolField, value: string): string | null {
  if (field.kind === "checkbox") {
    return field.required && value !== "true" ? (field.requiredMessage ?? REQUIRED_MESSAGE) : null;
  }
  if (field.kind !== "text") return null;
  const trimmed = value.trim();
  if (!trimmed) return field.required ? (field.requiredMessage ?? REQUIRED_MESSAGE) : null;
  return field.validate?.(trimmed) ?? null;
}

/** Primer error entre los campos visibles: es lo que se muestra junto al botón de acción. */
export function firstFieldError(fields: readonly ToolField[], values: FieldValues): string | null {
  for (const field of fields) {
    if (!isFieldVisible(field, values)) continue;
    const error = fieldError(field, values[field.name] ?? "");
    if (error) return error;
  }
  return null;
}

/** Solo campos visibles y con valor: el backend nunca recibe opciones que no aplican. */
export function submittableFields(
  fields: readonly ToolField[],
  values: FieldValues,
  fixed: FieldValues = {},
): Record<string, string> {
  const result: Record<string, string> = { ...fixed };
  for (const field of fields) {
    if (!isFieldVisible(field, values)) continue;
    const value = (values[field.name] ?? "").trim();
    if (value) result[field.name] = value;
  }
  return result;
}
