import type { LucideIcon } from "lucide-react";

import type { FileAccept } from "../lib/files";
import type { FileDownload } from "../services/apiClient";
import type { EngineId } from "../services/engineService";

export type ToolCategoryId = "organize" | "optimize" | "from-pdf" | "to-pdf" | "edit" | "ai";
export type ToolTone = "accent" | "success" | "warning" | "danger" | "teal" | "ink";

export interface ToolCategory {
  id: ToolCategoryId;
  title: string;
  tone: ToolTone;
}

// ——— Campos de opciones ———

/** El campo solo se muestra (y se envía) si otro campo tiene cierto valor. */
export interface FieldCondition {
  field: string;
  equals: string;
}

interface FieldBase {
  name: string;
  label: string;
  visibleWhen?: FieldCondition;
}

export interface ChoiceOption {
  value: string;
  label: string;
  description: string;
}

export interface ChoiceField extends FieldBase {
  kind: "choice";
  options: readonly ChoiceOption[];
  defaultValue: string;
  /** Nombre de otro campo cuyo valor no puede repetirse aquí (p. ej. idioma origen ≠ destino). */
  distinctFrom?: string;
}

export interface TextField extends FieldBase {
  kind: "text";
  defaultValue: string;
  maxLength: number;
  placeholder?: string;
  hint?: string;
  multiline?: boolean;
  numeric?: boolean;
  required?: boolean;
  requiredMessage?: string;
  /** Devuelve el mensaje de error o null si el valor (ya recortado) es válido. */
  validate?: (value: string) => string | null;
}

export interface CheckboxField extends FieldBase {
  kind: "checkbox";
  description: string;
  defaultValue: "true" | "false";
  required?: boolean;
  requiredMessage?: string;
}

export type ToolField = ChoiceField | TextField | CheckboxField;

// ——— Herramientas ———

interface ToolBase {
  id: string;
  /** Parte de la URL: #/<slug>. */
  slug: string;
  title: string;
  description: string;
  category: ToolCategoryId;
  icon: LucideIcon;
  /** Sinónimos para el buscador. */
  keywords?: readonly string[];
  actionLabel: string;
  workingLabel: string;
}

/** Un archivo entra, un archivo sale. Añadir una nueva = una entrada en el catálogo. */
export interface FileToolDefinition extends ToolBase {
  kind: "file";
  endpoint: string;
  accept: FileAccept;
  fields?: readonly ToolField[];
  /** Valores fijos que se envían siempre (p. ej. el formato de destino). */
  fixedFields?: Readonly<Record<string, string>>;
  requires?: EngineId;
  /** Frase extra para el aviso de éxito (p. ej. cuánto se ahorró). */
  describeResult?: (download: FileDownload) => string | null;
}

/** Varios archivos en una lista ordenable (unir PDF, imágenes a PDF). */
export interface MultiFileToolDefinition extends ToolBase {
  kind: "multi";
  endpoint: string;
  accept: FileAccept;
  minFiles: number;
  fields?: readonly ToolField[];
}

export type PageEditorMode = "organize" | "rotate" | "delete" | "extract";

/** Editor visual sobre las miniaturas de las páginas. */
export interface PageToolDefinition extends ToolBase {
  kind: "pages";
  mode: PageEditorMode;
}

/** Rellenar un formulario PDF con los campos que trae el propio documento. */
export interface FormToolDefinition extends ToolBase {
  kind: "form";
}

/** Editor visual: anotar, resaltar, dibujar, firmar y corregir texto sobre las páginas. */
export interface EditorToolDefinition extends ToolBase {
  kind: "editor";
  accept: FileAccept;
}

export type ToolDefinition =
  | FileToolDefinition
  | MultiFileToolDefinition
  | PageToolDefinition
  | FormToolDefinition
  | EditorToolDefinition;
