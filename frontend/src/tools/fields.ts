/** Opciones reutilizables de las herramientas. Los `name` y `value` son exactamente los que espera el backend. */

import type { CheckboxField, ChoiceField, TextField } from "./types";

export const COMPRESSION_LEVEL: ChoiceField = {
  kind: "choice",
  name: "level",
  label: "Nivel de compresión",
  defaultValue: "medium",
  options: [
    { value: "low", label: "Ligera", description: "Máxima calidad, algo menos de ahorro." },
    { value: "medium", label: "Recomendada", description: "Buen equilibrio entre peso y calidad." },
    { value: "high", label: "Fuerte", description: "El menor tamaño posible." },
  ],
};

// ——— Dividir ———

export const SPLIT_MODE: ChoiceField = {
  kind: "choice",
  name: "mode",
  label: "Cómo dividir",
  defaultValue: "pages",
  options: [
    { value: "pages", label: "Cada página", description: "Un PDF por página." },
    { value: "ranges", label: "Por rangos", description: "Tú eliges qué páginas van juntas." },
    { value: "fixed", label: "En bloques", description: "Grupos del mismo número de páginas." },
  ],
};

export const SPLIT_RANGES: TextField = {
  kind: "text",
  name: "ranges",
  label: "Rangos",
  defaultValue: "",
  placeholder: "1-3, 5, 8-",
  hint: "Separa con comas. «8-» significa de la 8 al final.",
  maxLength: 500,
  required: true,
  requiredMessage: "Escribe los rangos, por ejemplo: 1-3, 5.",
  visibleWhen: { field: "mode", equals: "ranges" },
  validate: (value) => (/^[\d\s,-]+$/.test(value) ? null : "Usa solo números, comas y guiones. Ej.: 1-3, 5, 8-"),
};

export const CHUNK_SIZE: TextField = {
  kind: "text",
  name: "chunk_size",
  label: "Páginas por archivo",
  defaultValue: "2",
  maxLength: 5,
  numeric: true,
  required: true,
  visibleWhen: { field: "mode", equals: "fixed" },
  validate: (value) => (/^[1-9]\d*$/.test(value) ? null : "Escribe un número entero mayor que 0."),
};

export const EXTRACT_OUTPUT: ChoiceField = {
  kind: "choice",
  name: "output",
  label: "Resultado",
  defaultValue: "single",
  options: [
    { value: "single", label: "Un solo PDF", description: "Las páginas elegidas, juntas." },
    { value: "separate", label: "Un PDF por página", description: "Varios archivos, juntos en un ZIP." },
  ],
};

// ——— Imágenes ———

export const IMAGE_FORMAT: ChoiceField = {
  kind: "choice",
  name: "image_format",
  label: "Formato",
  defaultValue: "jpg",
  options: [
    { value: "jpg", label: "JPG", description: "Archivos ligeros, ideal para fotos y compartir." },
    { value: "png", label: "PNG", description: "Sin pérdida, ideal para texto y gráficos." },
  ],
};

export const IMAGE_QUALITY: ChoiceField = {
  kind: "choice",
  name: "quality",
  label: "Resolución",
  defaultValue: "standard",
  options: [
    { value: "screen", label: "Pantalla", description: "96 ppp · para ver en el ordenador." },
    { value: "standard", label: "Estándar", description: "150 ppp · buena para casi todo." },
    { value: "high", label: "Alta", description: "300 ppp · para imprimir." },
  ],
};

export const IMAGE_PAGE_SIZE: ChoiceField = {
  kind: "choice",
  name: "page_size",
  label: "Tamaño de página",
  defaultValue: "original",
  options: [
    { value: "original", label: "Como la imagen", description: "Cada página adopta la forma de su imagen." },
    { value: "a4", label: "A4", description: "Todas iguales, con márgenes, listas para imprimir." },
  ],
};

// ——— Editar y proteger ———

export const OCR_LANGUAGE: ChoiceField = {
  kind: "choice",
  name: "language",
  label: "Idioma del documento",
  defaultValue: "spa",
  options: [
    { value: "spa", label: "Español", description: "La opción más precisa para textos en español." },
    { value: "eng", label: "Inglés", description: "Para documentos en inglés." },
    { value: "spa+eng", label: "Español e inglés", description: "Si el documento mezcla ambos." },
  ],
};

const TRANSLATE_LANGUAGE_OPTIONS = [
  { value: "es", label: "Español", description: "" },
  { value: "en", label: "Inglés", description: "" },
  { value: "fr", label: "Francés", description: "" },
  { value: "de", label: "Alemán", description: "" },
  { value: "ko", label: "Coreano", description: "" },
] as const;

export const TRANSLATE_SOURCE: ChoiceField = {
  kind: "choice",
  name: "source_lang",
  label: "Idioma del documento",
  defaultValue: "es",
  options: TRANSLATE_LANGUAGE_OPTIONS,
};

export const TRANSLATE_TARGET: ChoiceField = {
  kind: "choice",
  name: "target_lang",
  label: "Traducir a",
  defaultValue: "en",
  // El idioma de destino nunca puede ser el mismo que el de origen.
  distinctFrom: "source_lang",
  options: TRANSLATE_LANGUAGE_OPTIONS,
};

export const TRANSLATE_CONSENT: CheckboxField = {
  kind: "checkbox",
  name: "consent",
  label: "Acepto enviar el texto a Groq",
  description: "Solo se envía el texto necesario para traducir; no se envían el nombre del archivo ni sus metadatos.",
  defaultValue: "false",
  required: true,
  requiredMessage: "Acepta el envío del texto a Groq para continuar.",
};

export const WORD_ALLOW_PARTIAL: CheckboxField = {
  kind: "checkbox",
  name: "allow_partial",
  label: "Permitir Word parcial",
  description: "Úsalo solo para reintentar: puede omitir páginas con errores y el archivo se marcará como parcial.",
  defaultValue: "false",
  required: false,
};

export const WATERMARK_TEXT: TextField = {
  kind: "text",
  name: "text",
  label: "Texto",
  defaultValue: "CONFIDENCIAL",
  placeholder: "CONFIDENCIAL",
  maxLength: 80,
  required: true,
  requiredMessage: "Escribe el texto de la marca de agua.",
};

export const WATERMARK_LAYOUT: ChoiceField = {
  kind: "choice",
  name: "layout",
  label: "Posición",
  defaultValue: "diagonal",
  options: [
    { value: "diagonal", label: "Diagonal", description: "Cruza la página de esquina a esquina." },
    { value: "horizontal", label: "Horizontal", description: "Centrada y recta." },
  ],
};

export const WATERMARK_OPACITY: ChoiceField = {
  kind: "choice",
  name: "opacity",
  label: "Intensidad",
  defaultValue: "medium",
  options: [
    { value: "light", label: "Suave", description: "Casi no molesta al leer." },
    { value: "medium", label: "Media", description: "Visible sin tapar el contenido." },
    { value: "strong", label: "Marcada", description: "Imposible de pasar por alto." },
  ],
};

export const NUMBER_POSITION: ChoiceField = {
  kind: "choice",
  name: "position",
  label: "Posición",
  defaultValue: "bottom-center",
  options: [
    { value: "bottom-center", label: "Abajo al centro", description: "La opción clásica." },
    { value: "bottom-right", label: "Abajo a la derecha", description: "Habitual en informes." },
    { value: "top-right", label: "Arriba a la derecha", description: "Visible al hojear." },
  ],
};

export const NUMBER_STYLE: ChoiceField = {
  kind: "choice",
  name: "style",
  label: "Formato",
  defaultValue: "number",
  options: [
    { value: "number", label: "3", description: "Solo el número." },
    { value: "page-of-total", label: "Página 3 de 10", description: "Con el total de páginas." },
    { value: "fraction", label: "3 / 10", description: "Compacto, con el total." },
  ],
};

export const REDACTION_TERMS: TextField = {
  kind: "text",
  name: "terms",
  label: "Textos a censurar",
  defaultValue: "",
  placeholder: "Un texto por línea\nJuan Pérez\n12345678",
  hint: "Se borran todas las apariciones, sin distinguir mayúsculas.",
  maxLength: 5000,
  multiline: true,
  required: true,
  requiredMessage: "Escribe al menos un texto que quieras censurar.",
  validate: (value) =>
    value.split("\n").some((line) => line.trim().length === 1) ? "Cada texto debe tener al menos 2 caracteres." : null,
};

export const REDACTION_FILL: ChoiceField = {
  kind: "choice",
  name: "fill",
  label: "Relleno",
  defaultValue: "black",
  options: [
    { value: "black", label: "Negro", description: "Deja claro que hubo una censura." },
    { value: "white", label: "Blanco", description: "Más discreto." },
  ],
};
