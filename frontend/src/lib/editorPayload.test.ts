import { describe, expect, it } from "vitest";

import type { Annotation } from "../components/editor/types";
import { buildOperations, type PageSize } from "./editorPayload";

const PAGES: PageSize[] = [
  { width: 600, height: 800 },
  { width: 400, height: 400 },
];

describe("buildOperations", () => {
  it("exports a bounded multiline box without losing fractional font sizes", () => {
    expect(buildOperations([{ id: "box", kind: "textbox", page: 0, rect: { x0: 0.1, y0: 0.2, x1: 0.5, y1: 0.4 }, text: "Línea uno\nLínea dos", size: 6.5, color: [0, 0, 0] }], PAGES).operations).toEqual([
      { type: "add_textbox", page: 0, rect: { x0: 60, y0: 160, x1: 300, y1: 320 }, text: "Línea uno\nLínea dos", size: 6.5, color: [0, 0, 0] },
    ]);
  });

  it("keeps native field edits including an empty value and an unchecked box", () => {
    expect(buildOperations([
      { id: "name", kind: "field", page: 0, name: "Equipo", value: "", size: 8 },
      { id: "check", kind: "field", page: 0, name: "Cartas", value: false, size: 8 },
    ], PAGES).operations).toEqual([
      { type: "set_field", page: 0, name: "Equipo", value: "", size: 8 },
      { type: "set_field", page: 0, name: "Cartas", value: false },
    ]);
  });
  it("saves the moved/resized image rectangle with the original image index only", () => {
    const { operations } = buildOperations([
      { id: "img", kind: "image", page: 0, rect: { x0: 0.2, y0: 0.3, x1: 0.6, y1: 0.7 }, imageIndex: 1, previewUrl: "blob:preview" },
    ], PAGES);
    expect(operations).toEqual([
      { type: "add_image", page: 0, rect: { x0: 120, y0: 240, x1: 360, y1: 560 }, image: 1 },
    ]);
  });
  it("maps normalized coordinates to PDF points per page", () => {
    const annotations: Annotation[] = [
      { id: "1", kind: "text", page: 0, nx: 0.5, ny: 0.25, text: "Hola", size: 12, color: [0, 0, 0] },
      { id: "2", kind: "highlight", page: 1, rect: { x0: 0, y0: 0, x1: 0.5, y1: 0.5 }, color: [1, 1, 0] },
    ];

    const { operations } = buildOperations(annotations, PAGES);

    expect(operations[0]).toEqual({ type: "add_text", page: 0, x: 300, y: 200, text: "Hola", size: 12, color: [0, 0, 0] });
    expect(operations[1]).toMatchObject({ type: "highlight", page: 1, rect: { x0: 0, y0: 0, x1: 200, y1: 200 } });
  });

  it("skips empty text and unknown pages", () => {
    const annotations: Annotation[] = [
      { id: "1", kind: "text", page: 0, nx: 0.1, ny: 0.1, text: "   ", size: 12, color: [0, 0, 0] },
      { id: "2", kind: "patch", page: 9, rect: { x0: 0, y0: 0, x1: 1, y1: 1 }, text: "x", size: 12, color: [0, 0, 0], fill: [1, 1, 1] },
    ];

    expect(buildOperations(annotations, PAGES).operations).toHaveLength(0);
  });

  it("denormalizes every point of a drawing", () => {
    const annotations: Annotation[] = [
      { id: "1", kind: "draw", page: 0, strokes: [[[0, 0], [1, 1]]], color: [1, 0, 0], width: 2 },
    ];

    const { operations } = buildOperations(annotations, PAGES);

    expect(operations[0]).toMatchObject({ type: "draw", strokes: [[[0, 0], [600, 800]]] });
  });

  it("saves the opaque sampled patch background with its text color", () => {
    const annotations: Annotation[] = [
      { id: "patch", kind: "patch", page: 0, rect: { x0: 0.1, y0: 0.2, x1: 0.6, y1: 0.4 }, text: "Corregido", size: 16, color: [0.1, 0.2, 0.3], fill: [0.94, 0.88, 0.75] },
    ];
    expect(buildOperations(annotations, PAGES).operations).toEqual([
      { type: "patch_text", page: 0, rect: { x0: 60, y0: 160, x1: 360, y1: 320 }, text: "Corregido", size: 16, color: [0.1, 0.2, 0.3], fill: [0.94, 0.88, 0.75] },
    ]);
  });
});
