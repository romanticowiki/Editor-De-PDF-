/**
 * ID corto y único para claves de React y anotaciones.
 *
 * Usa `crypto.randomUUID` cuando está disponible, pero cae a un fallback si no: esa API solo
 * existe en contextos seguros (HTTPS o localhost) y es `undefined` al servir la app por HTTP en
 * red local (p. ej. http://192.168.x.x:8000), donde rompería la subida de imágenes.
 */
export function newId(): string {
  const c = globalThis.crypto;
  if (c && typeof c.randomUUID === "function") return c.randomUUID();
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}
