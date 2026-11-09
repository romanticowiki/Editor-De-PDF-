// Revocar la URL en el mismo tick puede cancelar la descarga en algunos navegadores.
const REVOKE_DELAY_MS = 30_000;

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.rel = "noopener";
  anchor.hidden = true;

  document.body.append(anchor);
  anchor.click();
  anchor.remove();

  window.setTimeout(() => URL.revokeObjectURL(url), REVOKE_DELAY_MS);
}
