/** Estado del editor visual de páginas. Funciones puras: la vista solo las llama. */

import type { PageCounts } from "../copy/messages";
import type { PagePreview } from "../services/pagesService";
import type { PageEditorMode } from "../tools/types";

export type Rotation = 0 | 90 | 180 | 270;

export interface EditablePage {
  id: string;
  /** Página original, desde 0. */
  index: number;
  /** Giro acumulado sin normalizar: permite animar siempre en el sentido del clic. */
  angle: number;
  removed: boolean;
  selected: boolean;
  thumbnail: string;
  width: number;
  height: number;
}

export interface PageInstruction {
  index: number;
  rotation: Rotation;
}

// Proporción de la tarjeta de miniatura (ancho / alto): aspect-[3/4].
const CARD_ASPECT = 3 / 4;

export function createPages(previews: readonly PagePreview[]): EditablePage[] {
  return previews.map((preview) => ({
    id: `p-${preview.number}`,
    index: preview.number - 1,
    angle: 0,
    removed: false,
    selected: false,
    thumbnail: preview.thumbnail,
    width: preview.width,
    height: preview.height,
  }));
}

export function normalizeRotation(angle: number): Rotation {
  return (((angle % 360) + 360) % 360) as Rotation;
}

export function isQuarterTurn(angle: number): boolean {
  return normalizeRotation(angle) % 180 === 90;
}

/** Escala para que una página girada 90° siga cabiendo en su tarjeta. */
export function quarterTurnScale(width: number, height: number): number {
  const aspect = width / height;
  // Tamaño mostrado sin girar, tomando el ancho de la tarjeta como 1.
  const shownWidth = aspect < CARD_ASPECT ? aspect / CARD_ASPECT : 1;
  const shownHeight = aspect < CARD_ASPECT ? 1 / CARD_ASPECT : 1 / aspect;
  // Girada, su alto debe caber en el ancho y su ancho en el alto.
  return Math.min(1, 1 / shownHeight, 1 / CARD_ASPECT / shownWidth);
}

export function rotatePages(pages: readonly EditablePage[], delta: 90 | -90, id?: string): EditablePage[] {
  return pages.map((page) => (id === undefined || page.id === id ? { ...page, angle: page.angle + delta } : page));
}

export function togglePage(pages: readonly EditablePage[], id: string, key: "removed" | "selected"): EditablePage[] {
  return pages.map((page) => (page.id === id ? { ...page, [key]: !page[key] } : page));
}

export function selectAllPages(pages: readonly EditablePage[], selected: boolean): EditablePage[] {
  return pages.map((page) => ({ ...page, selected }));
}

export function countPages(pages: readonly EditablePage[]): PageCounts {
  return {
    total: pages.length,
    kept: pages.filter((page) => !page.removed).length,
    rotated: pages.filter((page) => normalizeRotation(page.angle) !== 0).length,
    selected: pages.filter((page) => page.selected).length,
  };
}

/** Lista final que entiende el backend: orden de salida y giro de cada página. */
export function buildInstructions(mode: PageEditorMode, pages: readonly EditablePage[]): PageInstruction[] {
  const toInstruction = (page: EditablePage, keepRotation: boolean): PageInstruction => ({
    index: page.index,
    rotation: keepRotation ? normalizeRotation(page.angle) : 0,
  });

  switch (mode) {
    case "organize":
      return pages.filter((page) => !page.removed).map((page) => toInstruction(page, true));
    case "rotate":
      return pages.map((page) => toInstruction(page, true));
    case "delete":
      return pages.filter((page) => !page.removed).map((page) => toInstruction(page, false));
    case "extract":
      return pages.filter((page) => page.selected).map((page) => toInstruction(page, false));
  }
}
