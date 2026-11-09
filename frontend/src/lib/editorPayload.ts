import type { Annotation, NRect } from "../components/editor/types";

export interface PageSize {
  width: number;
  height: number;
}

type Operation = Record<string, unknown>;

/** Convierte las anotaciones (normalizadas) al JSON exacto que espera el backend (puntos PDF). */
export function buildOperations(annotations: readonly Annotation[], pages: readonly PageSize[]): { operations: Operation[] } {
  const operations: Operation[] = [];

  for (const annotation of annotations) {
    const page = pages[annotation.page];
    if (!page) continue;

    switch (annotation.kind) {
      case "field":
        operations.push({ type: "set_field", page: annotation.page, name: annotation.name, value: annotation.value, ...(typeof annotation.value === "string" ? { size: annotation.size } : {}) });
        break;
      case "textbox":
        if (annotation.text.trim()) operations.push({ type: "add_textbox", page: annotation.page, rect: denormalize(annotation.rect, page), text: annotation.text, size: annotation.size, color: annotation.color });
        break;
      case "text":
        if (!annotation.text.trim()) break;
        operations.push({
          type: "add_text",
          page: annotation.page,
          x: annotation.nx * page.width,
          y: annotation.ny * page.height,
          text: annotation.text,
          size: annotation.size,
          color: annotation.color,
        });
        break;
      case "highlight":
        operations.push({ type: "highlight", page: annotation.page, rect: denormalize(annotation.rect, page), color: annotation.color });
        break;
      case "patch":
        if (!annotation.text.trim()) break;
        operations.push({
          type: "patch_text",
          page: annotation.page,
          rect: denormalize(annotation.rect, page),
          text: annotation.text,
          size: annotation.size,
          color: annotation.color,
          fill: annotation.fill,
        });
        break;
      case "draw":
        operations.push({
          type: "draw",
          page: annotation.page,
          strokes: annotation.strokes.map((stroke) => stroke.map(([nx, ny]) => [nx * page.width, ny * page.height])),
          color: annotation.color,
          width: annotation.width,
        });
        break;
      case "image":
        operations.push({ type: "add_image", page: annotation.page, rect: denormalize(annotation.rect, page), image: annotation.imageIndex });
        break;
    }
  }

  return { operations };
}

function denormalize(rect: NRect, page: PageSize) {
  return { x0: rect.x0 * page.width, y0: rect.y0 * page.height, x1: rect.x1 * page.width, y1: rect.y1 * page.height };
}
