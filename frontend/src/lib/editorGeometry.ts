import type { NRect } from "../components/editor/types";

export type ImageCorner = "nw" | "ne" | "sw" | "se";

const MIN_IMAGE_SIZE = 0.01;

export function moveImageRect(rect: NRect, dx: number, dy: number): NRect {
  const x = Math.max(-rect.x0, Math.min(dx, 1 - rect.x1));
  const y = Math.max(-rect.y0, Math.min(dy, 1 - rect.y1));
  return { x0: rect.x0 + x, y0: rect.y0 + y, x1: rect.x1 + x, y1: rect.y1 + y };
}

/**
 * Redimensiona desde una esquina **bloqueando la proporción** de la imagen: el marco abraza la
 * imagen real (sin huecos). La esquina opuesta queda fija; se respeta un tamaño mínimo, se recorta
 * a la página y, si el puntero cruza la esquina opuesta, colapsa al mínimo en vez de invertirse.
 * (`targetX`/`targetY` son la posición normalizada 0..1 a la que se arrastra la esquina.)
 */
export function resizeImageRect(
  rect: NRect,
  corner: ImageCorner,
  targetX: number,
  targetY: number,
  width: number,
  height: number,
): NRect {
  const ratio = pageAspect(rect, width, height);
  const fixedX = corner.includes("w") ? rect.x1 : rect.x0;
  const fixedY = corner.includes("n") ? rect.y1 : rect.y0;
  const dirX = corner.includes("w") ? -1 : 1;
  const dirY = corner.includes("n") ? -1 : 1;
  // Ancho deseado (en puntos) desde la esquina fija; con signo, para que cruzar la esquina colapse.
  const wantWpt = Math.max((targetX - fixedX) * dirX * width, (targetY - fixedY) * dirY * height * ratio);
  return sizedRect(rect, corner, wantWpt, width, height);
}

/** Crece (`deltaPt > 0`) o encoge (`< 0`) la imagen manteniendo proporción. Para el teclado. */
export function scaleImageRect(rect: NRect, corner: ImageCorner, deltaPt: number, width: number, height: number): NRect {
  const currentWpt = (rect.x1 - rect.x0) * width;
  return sizedRect(rect, corner, currentWpt + deltaPt, width, height);
}

export function imageRect(nx: number, ny: number, aspect: number, width: number, height: number): NRect {
  const nWidth = Math.min(0.28, (aspect * height) / width);
  const nHeight = (nWidth * width) / aspect / height;
  const x0 = Math.max(0, Math.min(nx - nWidth / 2, 1 - nWidth));
  const y0 = Math.max(0, Math.min(ny - nHeight / 2, 1 - nHeight));
  return { x0, y0, x1: x0 + nWidth, y1: y0 + nHeight };
}

/** Proporción ancho/alto del marco en puntos de página (lo que mantiene a la imagen sin deformar). */
function pageAspect(rect: NRect, width: number, height: number): number {
  return ((rect.x1 - rect.x0) * width) / ((rect.y1 - rect.y0) * height);
}

/** Construye el rectángulo con un ancho objetivo (en puntos), anclado en la esquina opuesta y proporcional. */
function sizedRect(rect: NRect, corner: ImageCorner, wantWpt: number, width: number, height: number): NRect {
  const ratio = pageAspect(rect, width, height);
  const fixedX = corner.includes("w") ? rect.x1 : rect.x0;
  const fixedY = corner.includes("n") ? rect.y1 : rect.y0;
  const dirX = corner.includes("w") ? -1 : 1;
  const dirY = corner.includes("n") ? -1 : 1;
  // Mínimo que garantiza ambos lados >= MIN_IMAGE_SIZE; máximo que no se sale de la página.
  const minWpt = Math.max(MIN_IMAGE_SIZE * width, MIN_IMAGE_SIZE * height * ratio);
  const maxWpt = Math.min((dirX > 0 ? 1 - fixedX : fixedX) * width, (dirY > 0 ? 1 - fixedY : fixedY) * height * ratio);
  const wpt = Math.min(Math.max(wantWpt, minWpt), Math.max(maxWpt, minWpt));
  const movedX = fixedX + (dirX * wpt) / width;
  const movedY = fixedY + (dirY * wpt) / ratio / height;
  return {
    x0: Math.min(fixedX, movedX),
    y0: Math.min(fixedY, movedY),
    x1: Math.max(fixedX, movedX),
    y1: Math.max(fixedY, movedY),
  };
}
