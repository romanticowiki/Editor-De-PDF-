const PDF_MIME = "application/pdf";

export interface FileAccept {
  readonly extensions: readonly string[];
  /** Cómo se nombra en frases: «Esta herramienta acepta un PDF». */
  readonly label: string;
}

export type RejectionReason = "wrong_type" | "empty" | "too_large" | "duplicate" | "limit_reached";

export interface FileRejection {
  fileName: string;
  reason: RejectionReason;
}

export interface FileLimits {
  maxFiles: number;
  maxFileBytes: number;
  accept: FileAccept;
}

export function matchesAccept(file: File, accept: FileAccept): boolean {
  const name = file.name.toLowerCase();
  if (accept.extensions.some((extension) => name.endsWith(extension))) return true;
  // Algunos navegadores entregan PDFs sin extensión pero con su tipo MIME.
  return accept.extensions.includes(".pdf") && file.type === PDF_MIME;
}

export function acceptAttribute(accept: FileAccept): string {
  return accept.extensions.join(",");
}

function fingerprint(file: File): string {
  return `${file.name}:${file.size}:${file.lastModified}`;
}

/** Separa los archivos entrantes en aceptados y rechazados (con motivo). Función pura. */
export function partitionFiles(
  existing: readonly File[],
  incoming: readonly File[],
  limits: FileLimits,
): { accepted: File[]; rejected: FileRejection[] } {
  const seen = new Set(existing.map(fingerprint));
  const accepted: File[] = [];
  const rejected: FileRejection[] = [];

  for (const file of incoming) {
    const reason = findRejectionReason(file, seen, existing.length + accepted.length, limits);
    if (reason) {
      rejected.push({ fileName: file.name, reason });
      continue;
    }
    seen.add(fingerprint(file));
    accepted.push(file);
  }

  return { accepted, rejected };
}

function findRejectionReason(
  file: File,
  seen: ReadonlySet<string>,
  currentCount: number,
  limits: FileLimits,
): RejectionReason | null {
  if (!matchesAccept(file, limits.accept)) return "wrong_type";
  if (file.size === 0) return "empty";
  if (file.size > limits.maxFileBytes) return "too_large";
  if (seen.has(fingerprint(file))) return "duplicate";
  if (currentCount >= limits.maxFiles) return "limit_reached";
  return null;
}

const sizeFormatter = new Intl.NumberFormat("es", { maximumFractionDigits: 1 });
const UNITS = ["B", "KB", "MB", "GB"] as const;

export function formatBytes(bytes: number): string {
  let value = bytes;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < UNITS.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${sizeFormatter.format(value)} ${UNITS[unitIndex]}`;
}
