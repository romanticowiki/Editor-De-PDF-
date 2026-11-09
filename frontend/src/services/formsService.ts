import { isRecord } from "../lib/guards";
import { ApiError, requestJson } from "./apiClient";

export type FormFieldKind = "text" | "checkbox" | "radio" | "choice";
export type FormValue = string | boolean;

export interface FormFieldInfo {
  name: string;
  kind: FormFieldKind;
  label: string;
  value: FormValue;
  options: string[];
  page: number;
  multiline: boolean;
  maxLength: number | null;
  readOnly: boolean;
}

const KINDS: ReadonlySet<string> = new Set<FormFieldKind>(["text", "checkbox", "radio", "choice"]);
const FIELDS_TIMEOUT_MS = 60_000;

export function fetchFormFields(file: File, signal?: AbortSignal): Promise<FormFieldInfo[]> {
  const body = new FormData();
  body.append("file", file, file.name);
  return requestJson("/forms/fields", parseFields, { method: "POST", body, signal, timeoutMs: FIELDS_TIMEOUT_MS });
}

function parseFields(data: unknown): FormFieldInfo[] {
  if (!isRecord(data) || !Array.isArray(data.fields)) throw new ApiError("server");
  return data.fields.map(parseField);
}

function parseField(raw: unknown): FormFieldInfo {
  if (
    !isRecord(raw) ||
    typeof raw.name !== "string" ||
    typeof raw.kind !== "string" ||
    !KINDS.has(raw.kind) ||
    typeof raw.label !== "string" ||
    !(typeof raw.value === "string" || typeof raw.value === "boolean") ||
    !Array.isArray(raw.options) ||
    typeof raw.page !== "number"
  ) {
    throw new ApiError("server");
  }
  return {
    name: raw.name,
    kind: raw.kind as FormFieldKind,
    label: raw.label,
    value: raw.value,
    options: raw.options.filter((option): option is string => typeof option === "string"),
    page: raw.page,
    multiline: raw.multiline === true,
    maxLength: typeof raw.max_length === "number" ? raw.max_length : null,
    readOnly: raw.read_only === true,
  };
}
