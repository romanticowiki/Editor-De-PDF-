import {
  AlignLeft,
  Archive,
  BookOpen,
  ClipboardPen,
  Code,
  Combine,
  EyeOff,
  FileOutput,
  FileText,
  FileType,
  Hash,
  ImageDown,
  Images,
  Languages,
  LayoutGrid,
  ListOrdered,
  Presentation,
  RotateCw,
  ScanText,
  Scissors,
  Sheet,
  Shrink,
  Sparkles,
  SquarePen,
  Stamp,
  Trash2,
} from "lucide-react";

import {
  compressionSummary,
  ocrSummary,
  redactionSummary,
  zipSummary,
} from "../copy/messages";
import type { EngineAvailability, EngineId } from "../services/engineService";
import {
  EPUB_ACCEPT,
  EXCEL_ACCEPT,
  HTML_ACCEPT,
  IMAGE_ACCEPT,
  MARKDOWN_ACCEPT,
  MARKDOWN_SOURCE_ACCEPT,
  OPENDOCUMENT_ACCEPT,
  PDF_ACCEPT,
  POWERPOINT_ACCEPT,
  RTF_ACCEPT,
  TXT_ACCEPT,
  WORD_ACCEPT,
} from "./accept";
import { CHUNK_SIZE, COMPRESSION_LEVEL, IMAGE_FORMAT, IMAGE_PAGE_SIZE, IMAGE_QUALITY, NUMBER_POSITION, NUMBER_STYLE, OCR_LANGUAGE, REDACTION_FILL, REDACTION_TERMS, SPLIT_MODE, SPLIT_RANGES, TRANSLATE_CONSENT, TRANSLATE_SOURCE, TRANSLATE_TARGET, WATERMARK_LAYOUT, WATERMARK_OPACITY, WATERMARK_TEXT, WORD_ALLOW_PARTIAL } from "./fields";
import type { ToolCategory, ToolCategoryId, ToolDefinition } from "./types";

export const TOOL_CATEGORIES: Record<ToolCategoryId, ToolCategory> = {
  organize: { id: "organize", title: "Organizar", tone: "accent" },
  optimize: { id: "optimize", title: "Optimizar", tone: "success" },
  "from-pdf": { id: "from-pdf", title: "Convertir desde PDF", tone: "warning" },
  "to-pdf": { id: "to-pdf", title: "Convertir a PDF", tone: "danger" },
  edit: { id: "edit", title: "Editar y proteger", tone: "teal" },
  ai: { id: "ai", title: "Para IA", tone: "ink" },
};

const CATEGORY_ORDER: readonly ToolCategoryId[] = ["organize", "optimize", "from-pdf", "to-pdf", "edit", "ai"];

const CONVERTING = "Convirtiendo…";
const APPLYING = "Aplicando…";

const OFFICE_TO_PDF = {
  kind: "file",
  category: "to-pdf",
  endpoint: "/convert/office-to-pdf",
  actionLabel: "Convertir a PDF",
  workingLabel: CONVERTING,
  requires: "office",
} as const;

const DOCUMENT_TO_PDF = {
  kind: "file",
  category: "to-pdf",
  endpoint: "/convert/document-to-pdf",
  actionLabel: "Convertir a PDF",
  workingLabel: CONVERTING,
} as const;

const FROM_PDF = { kind: "file", category: "from-pdf", accept: PDF_ACCEPT, workingLabel: CONVERTING } as const;

const MARKDOWN_EXPORT = {
  kind: "file",
  category: "ai",
  endpoint: "/convert/markdown",
  accept: MARKDOWN_ACCEPT,
  workingLabel: CONVERTING,
  keywords: ["md", "markdown", "ia", "claude", "llm"],
} as const;

const PAGE_EDITOR = { kind: "pages", category: "organize", workingLabel: APPLYING } as const;

export const TOOLS: readonly ToolDefinition[] = [
  // ——— Organizar ———
  {
    kind: "multi",
    id: "merge",
    slug: "unir-pdf",
    title: "Unir PDF",
    description: "Junta varios PDF en uno y elige el orden.",
    category: "organize",
    icon: Combine,
    endpoint: "/merge",
    accept: PDF_ACCEPT,
    minFiles: 2,
    actionLabel: "Unir y descargar",
    workingLabel: "Uniendo…",
    keywords: ["combinar", "juntar"],
  },
  {
    kind: "file",
    id: "split",
    slug: "dividir-pdf",
    title: "Dividir PDF",
    description: "Separa páginas sueltas, rangos o bloques iguales.",
    category: "organize",
    icon: Scissors,
    endpoint: "/pages/split",
    accept: PDF_ACCEPT,
    fields: [SPLIT_MODE, SPLIT_RANGES, CHUNK_SIZE],
    actionLabel: "Dividir",
    workingLabel: "Dividiendo…",
    describeResult: zipSummary({ singular: "archivo", plural: "archivos" }),
    keywords: ["separar", "partir", "rangos"],
  },
  {
    ...PAGE_EDITOR,
    id: "organize",
    slug: "organizar-pdf",
    mode: "organize",
    title: "Organizar PDF",
    description: "Reordena, gira y quita páginas arrastrándolas.",
    icon: LayoutGrid,
    actionLabel: "Guardar y descargar",
    keywords: ["ordenar", "reordenar", "mover"],
  },
  {
    ...PAGE_EDITOR,
    id: "rotate",
    slug: "girar-pdf",
    mode: "rotate",
    title: "Girar PDF",
    description: "Endereza las páginas que están de lado o al revés.",
    icon: RotateCw,
    actionLabel: "Aplicar giros",
    keywords: ["rotar", "voltear"],
  },
  {
    ...PAGE_EDITOR,
    id: "delete-pages",
    slug: "eliminar-paginas",
    mode: "delete",
    title: "Eliminar páginas",
    description: "Quita las páginas que sobran.",
    icon: Trash2,
    actionLabel: "Eliminar y descargar",
    keywords: ["borrar", "quitar"],
  },
  {
    ...PAGE_EDITOR,
    id: "extract-pages",
    slug: "extraer-paginas",
    mode: "extract",
    title: "Extraer páginas",
    description: "Saca las páginas que necesitas a un PDF nuevo.",
    icon: FileOutput,
    actionLabel: "Extraer",
    keywords: ["sacar", "copiar"],
  },

  // ——— Optimizar ———
  {
    kind: "file",
    id: "compress",
    slug: "comprimir-pdf",
    title: "Comprimir PDF",
    description: "Reduce el peso sin perder legibilidad.",
    category: "optimize",
    icon: Shrink,
    endpoint: "/compress",
    accept: PDF_ACCEPT,
    actionLabel: "Comprimir",
    workingLabel: "Comprimiendo…",
    fields: [COMPRESSION_LEVEL],
    describeResult: compressionSummary,
    keywords: ["reducir", "tamaño", "peso", "optimizar"],
  },
  {
    kind: "file",
    id: "pdfa",
    slug: "pdf-a-pdfa",
    title: "PDF a PDF/A",
    description: "Formato estable para guardar documentos durante años.",
    category: "optimize",
    icon: Archive,
    endpoint: "/convert/pdf-to-pdfa",
    accept: PDF_ACCEPT,
    actionLabel: "Convertir a PDF/A",
    workingLabel: CONVERTING,
    keywords: ["archivo", "iso", "conservar"],
  },

  // ——— Convertir desde PDF ———
  {
    ...FROM_PDF,
    id: "pdf-to-word",
    slug: "pdf-a-word",
    title: "PDF a Word",
    description: "Convierte tu PDF en un documento editable.",
    icon: FileText,
    endpoint: "/convert/pdf-to-word",
    fields: [WORD_ALLOW_PARTIAL],
    actionLabel: "Convertir a Word",
    keywords: ["docx", "editar"],
  },
  {
    ...FROM_PDF,
    id: "pdf-to-excel",
    slug: "pdf-a-excel",
    title: "PDF a Excel",
    description: "Pasa las tablas del PDF a una hoja de cálculo.",
    icon: Sheet,
    endpoint: "/convert/pdf-to-excel",
    actionLabel: "Convertir a Excel",
    keywords: ["xlsx", "tablas"],
  },
  {
    ...FROM_PDF,
    id: "pdf-to-powerpoint",
    slug: "pdf-a-powerpoint",
    title: "PDF a PowerPoint",
    description: "Cada página se convierte en una diapositiva.",
    icon: Presentation,
    endpoint: "/convert/pdf-to-powerpoint",
    actionLabel: "Convertir a PowerPoint",
    keywords: ["pptx", "ppt", "diapositivas"],
  },
  {
    ...FROM_PDF,
    id: "pdf-to-images",
    slug: "pdf-a-imagen",
    title: "PDF a JPG o PNG",
    description: "Guarda cada página como una imagen nítida.",
    icon: ImageDown,
    endpoint: "/convert/pdf-to-images",
    fields: [IMAGE_FORMAT, IMAGE_QUALITY],
    actionLabel: "Convertir a imágenes",
    describeResult: zipSummary({ singular: "imagen", plural: "imágenes" }),
    keywords: ["jpg", "png", "imagen", "foto"],
  },

  // ——— Convertir a PDF ———
  {
    kind: "multi",
    id: "images-to-pdf",
    slug: "imagen-a-pdf",
    title: "JPG o PNG a PDF",
    description: "Convierte fotos e imágenes en un PDF, en el orden que elijas.",
    category: "to-pdf",
    icon: Images,
    endpoint: "/convert/images-to-pdf",
    accept: IMAGE_ACCEPT,
    minFiles: 1,
    fields: [IMAGE_PAGE_SIZE],
    actionLabel: "Crear PDF",
    workingLabel: "Creando…",
    keywords: ["jpg", "png", "foto", "imagen", "escanear"],
  },
  {
    ...OFFICE_TO_PDF,
    id: "word-to-pdf",
    slug: "word-a-pdf",
    title: "Word a PDF",
    description: "Convierte documentos .docx y .doc.",
    icon: FileText,
    accept: WORD_ACCEPT,
  },
  {
    ...OFFICE_TO_PDF,
    id: "excel-to-pdf",
    slug: "excel-a-pdf",
    title: "Excel a PDF",
    description: "Convierte hojas de cálculo .xlsx y .xls.",
    icon: Sheet,
    accept: EXCEL_ACCEPT,
  },
  {
    ...OFFICE_TO_PDF,
    id: "powerpoint-to-pdf",
    slug: "powerpoint-a-pdf",
    title: "PowerPoint a PDF",
    description: "Convierte presentaciones .pptx y .ppt.",
    icon: Presentation,
    accept: POWERPOINT_ACCEPT,
    keywords: ["ppt"],
  },
  {
    ...OFFICE_TO_PDF,
    id: "opendocument-to-pdf",
    slug: "openoffice-a-pdf",
    title: "OpenOffice a PDF",
    description: "Convierte archivos .odt, .ods y .odp.",
    icon: FileType,
    accept: OPENDOCUMENT_ACCEPT,
    keywords: ["odt", "libreoffice"],
  },
  {
    ...OFFICE_TO_PDF,
    id: "rtf-to-pdf",
    slug: "rtf-a-pdf",
    title: "RTF a PDF",
    description: "Convierte documentos de texto enriquecido.",
    icon: FileType,
    accept: RTF_ACCEPT,
  },
  {
    ...DOCUMENT_TO_PDF,
    id: "txt-to-pdf",
    slug: "txt-a-pdf",
    title: "TXT a PDF",
    description: "Convierte texto plano en un PDF bien maquetado.",
    icon: AlignLeft,
    accept: TXT_ACCEPT,
    keywords: ["texto"],
  },
  {
    ...DOCUMENT_TO_PDF,
    id: "html-to-pdf",
    slug: "html-a-pdf",
    title: "HTML a PDF",
    description: "Guarda una página HTML como PDF.",
    icon: Code,
    accept: HTML_ACCEPT,
    keywords: ["web"],
  },
  {
    ...DOCUMENT_TO_PDF,
    id: "epub-to-pdf",
    slug: "epub-a-pdf",
    title: "EPUB a PDF",
    description: "Convierte libros electrónicos a PDF.",
    icon: BookOpen,
    accept: EPUB_ACCEPT,
    keywords: ["libro", "ebook"],
  },

  // ——— Editar y proteger ———
  {
    kind: "editor",
    id: "editor",
    slug: "editor-pdf",
    title: "Editor de PDF",
    description: "Anota, resalta, dibuja, añade imágenes o firmas y corrige texto sobre tus páginas.",
    category: "edit",
    icon: SquarePen,
    accept: PDF_ACCEPT,
    actionLabel: "Guardar cambios",
    workingLabel: "Guardando…",
    keywords: ["editar", "anotar", "firmar", "firma", "resaltar", "dibujar", "corregir", "sello", "imagen", "sticker", "png", "jpg"],
  },
  {
    kind: "file",
    id: "ocr",
    slug: "ocr-pdf",
    title: "OCR en PDF",
    description: "Convierte un escaneo en texto que se puede buscar y copiar.",
    category: "edit",
    icon: ScanText,
    endpoint: "/ocr",
    accept: PDF_ACCEPT,
    fields: [OCR_LANGUAGE],
    requires: "ocr",
    actionLabel: "Reconocer texto",
    workingLabel: "Reconociendo…",
    describeResult: ocrSummary,
    keywords: ["escaneo", "reconocer", "texto", "tesseract"],
  },
  {
    kind: "file",
    id: "translate",
    slug: "traducir-pdf",
    title: "Traducir PDF",
    description: "Cambia el idioma del texto conservando el diseño. Usa un servicio en la nube.",
    category: "edit",
    icon: Languages,
    endpoint: "/translate",
    accept: PDF_ACCEPT,
    fields: [TRANSLATE_SOURCE, TRANSLATE_TARGET, TRANSLATE_CONSENT],
    requires: "translate",
    actionLabel: "Traducir",
    workingLabel: "Traduciendo…",
    keywords: ["traducir", "idioma", "translate", "inglés", "francés", "alemán", "coreano", "groq"],
  },
  {
    kind: "file",
    id: "watermark",
    slug: "marca-de-agua",
    title: "Marca de agua",
    description: "Añade un texto como «Confidencial» sobre cada página.",
    category: "edit",
    icon: Stamp,
    endpoint: "/edit/watermark",
    accept: PDF_ACCEPT,
    fields: [WATERMARK_TEXT, WATERMARK_LAYOUT, WATERMARK_OPACITY],
    actionLabel: "Añadir marca de agua",
    workingLabel: APPLYING,
    keywords: ["sello", "confidencial", "borrador"],
  },
  {
    kind: "file",
    id: "page-numbers",
    slug: "numerar-paginas",
    title: "Numerar páginas",
    description: "Pon el número de página donde prefieras.",
    category: "edit",
    icon: ListOrdered,
    endpoint: "/edit/page-numbers",
    accept: PDF_ACCEPT,
    fields: [NUMBER_POSITION, NUMBER_STYLE],
    actionLabel: "Numerar",
    workingLabel: APPLYING,
    keywords: ["paginación", "números"],
  },
  {
    kind: "file",
    id: "redact",
    slug: "censurar-pdf",
    title: "Censurar PDF",
    description: "Borra de verdad datos sensibles: no solo los tapa.",
    category: "edit",
    icon: EyeOff,
    endpoint: "/security/redact",
    accept: PDF_ACCEPT,
    fields: [REDACTION_TERMS, REDACTION_FILL],
    actionLabel: "Censurar",
    workingLabel: "Censurando…",
    describeResult: redactionSummary,
    keywords: ["redactar", "ocultar", "tachar", "datos personales"],
  },
  {
    kind: "form",
    id: "fill-form",
    slug: "rellenar-formulario",
    title: "Rellenar formulario",
    description: "Completa los campos de un formulario PDF y fíjalos.",
    category: "edit",
    icon: ClipboardPen,
    actionLabel: "Rellenar y descargar",
    workingLabel: "Guardando…",
    keywords: ["formulario", "campos", "aplanar", "acroform"],
  },

  // ——— Para IA ———
  {
    kind: "file",
    id: "to-markdown",
    slug: "documento-a-markdown",
    title: "Documento a Markdown",
    description: "Texto limpio y estructurado, listo para Claude.",
    category: "ai",
    icon: Sparkles,
    endpoint: "/convert/to-markdown",
    accept: MARKDOWN_SOURCE_ACCEPT,
    actionLabel: "Convertir a Markdown",
    workingLabel: CONVERTING,
    keywords: ["ia", "llm", "claude", "markitdown", "md"],
  },
  {
    ...MARKDOWN_EXPORT,
    id: "markdown-to-pdf",
    slug: "markdown-a-pdf",
    title: "Markdown a PDF",
    description: "Convierte tus notas .md en un PDF con buen formato.",
    icon: Hash,
    fixedFields: { target: "pdf" },
    actionLabel: "Convertir a PDF",
  },
  {
    ...MARKDOWN_EXPORT,
    id: "markdown-to-word",
    slug: "markdown-a-word",
    title: "Markdown a Word",
    description: "Títulos, listas y tablas pasan a un .docx editable.",
    icon: Hash,
    fixedFields: { target: "docx" },
    actionLabel: "Convertir a Word",
  },
  {
    ...MARKDOWN_EXPORT,
    id: "markdown-to-powerpoint",
    slug: "markdown-a-powerpoint",
    title: "Markdown a PowerPoint",
    description: "Cada título se convierte en una diapositiva.",
    icon: Hash,
    fixedFields: { target: "pptx" },
    actionLabel: "Convertir a PowerPoint",
  },
];

export function findToolBySlug(slug: string): ToolDefinition | undefined {
  return TOOLS.find((tool) => tool.slug === slug);
}

export function missingEngine(tool: ToolDefinition, engines: EngineAvailability): EngineId | null {
  if (tool.kind !== "file" || tool.requires === undefined) return null;
  // Solo bloqueamos si el backend confirmó que falta; sin datos, dejamos intentar.
  return engines[tool.requires] === false ? tool.requires : null;
}

function normalize(text: string): string {
  return text.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
}

export function filterTools(tools: readonly ToolDefinition[], query: string): readonly ToolDefinition[] {
  const terms = normalize(query).split(/\s+/).filter(Boolean);
  if (terms.length === 0) return tools;

  return tools.filter((tool) => {
    const haystack = normalize(
      [tool.title, tool.description, TOOL_CATEGORIES[tool.category].title, ...(tool.keywords ?? [])].join(" "),
    );
    return terms.every((term) => haystack.includes(term));
  });
}

export function groupByCategory(tools: readonly ToolDefinition[]): Array<{ category: ToolCategory; tools: ToolDefinition[] }> {
  return CATEGORY_ORDER.map((id) => ({
    category: TOOL_CATEGORIES[id],
    tools: tools.filter((tool) => tool.category === id),
  })).filter((group) => group.tools.length > 0);
}
