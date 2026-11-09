import type { FileAccept } from "../lib/files";

// Espejo de los formatos que acepta cada ruta del backend (app/core/file_types.py).
export const PDF_ACCEPT = { extensions: [".pdf"], label: "un PDF" } as const satisfies FileAccept;
export const WORD_ACCEPT = { extensions: [".docx", ".doc"], label: "un documento de Word" } as const satisfies FileAccept;
export const EXCEL_ACCEPT = { extensions: [".xlsx", ".xls"], label: "una hoja de Excel" } as const satisfies FileAccept;
export const POWERPOINT_ACCEPT = {
  extensions: [".pptx", ".ppt"],
  label: "una presentación de PowerPoint",
} as const satisfies FileAccept;
export const OPENDOCUMENT_ACCEPT = {
  extensions: [".odt", ".ods", ".odp"],
  label: "un documento de OpenOffice",
} as const satisfies FileAccept;
export const RTF_ACCEPT = { extensions: [".rtf"], label: "un archivo RTF" } as const satisfies FileAccept;
export const TXT_ACCEPT = { extensions: [".txt"], label: "un archivo de texto" } as const satisfies FileAccept;
export const HTML_ACCEPT = { extensions: [".html", ".htm"], label: "una página HTML" } as const satisfies FileAccept;
export const EPUB_ACCEPT = { extensions: [".epub"], label: "un libro EPUB" } as const satisfies FileAccept;
export const IMAGE_ACCEPT = {
  extensions: [".jpg", ".jpeg", ".png"],
  label: "imágenes JPG o PNG",
} as const satisfies FileAccept;
export const MARKDOWN_ACCEPT = { extensions: [".md", ".markdown"], label: "un archivo Markdown" } as const satisfies FileAccept;
export const MARKDOWN_SOURCE_ACCEPT = {
  extensions: [".pdf", ".docx", ".xlsx", ".pptx", ".html", ".htm", ".txt", ".epub"],
  label: "un PDF, Word, Excel, PowerPoint, HTML, TXT o EPUB",
} as const satisfies FileAccept;
