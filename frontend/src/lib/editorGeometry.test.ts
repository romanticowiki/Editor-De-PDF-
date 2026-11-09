import { describe, expect, it } from "vitest";

import { imageRect, moveImageRect, resizeImageRect, scaleImageRect, type ImageCorner } from "./editorGeometry";

const RECT = { x0: 0.2, y0: 0.3, x1: 0.6, y1: 0.7 };
// Página no cuadrada a propósito: así el bloqueo de proporción se mide en puntos, no en fracciones.
const W = 1000;
const H = 500;
const pageAspect = (r: typeof RECT) => ((r.x1 - r.x0) * W) / ((r.y1 - r.y0) * H);

describe("image manipulation", () => {
  it("moves without changing size, including at the page boundaries", () => {
    expect(moveImageRect(RECT, 0.1, -0.1)).toEqual({ x0: expect.closeTo(0.3), y0: expect.closeTo(0.2), x1: expect.closeTo(0.7), y1: expect.closeTo(0.6) });
    const moved = moveImageRect(RECT, 2, -2);
    expect(moved.x1).toBe(1);
    expect(moved.y0).toBe(0);
    expect(moved.x1 - moved.x0).toBeCloseTo(0.4);
    expect(moved.y1 - moved.y0).toBeCloseTo(0.4);
  });

  it.each<ImageCorner>(["nw", "ne", "sw", "se"])("resizes %s keeping the opposite corner fixed and the aspect locked", (corner) => {
    const left = corner.includes("w");
    const top = corner.includes("n");
    const resized = resizeImageRect(RECT, corner, left ? 0.05 : 0.95, top ? 0.05 : 0.95, W, H);
    // La esquina OPUESTA no se mueve.
    expect(resized[left ? "x1" : "x0"]).toBeCloseTo(RECT[left ? "x1" : "x0"]);
    expect(resized[top ? "y1" : "y0"]).toBeCloseTo(RECT[top ? "y1" : "y0"]);
    // La proporción (en puntos de página) se conserva → sin huecos.
    expect(pageAspect(resized)).toBeCloseTo(pageAspect(RECT));
    // Nunca se sale de la página.
    expect(resized.x0).toBeGreaterThanOrEqual(0);
    expect(resized.y0).toBeGreaterThanOrEqual(0);
    expect(resized.x1).toBeLessThanOrEqual(1 + 1e-9);
    expect(resized.y1).toBeLessThanOrEqual(1 + 1e-9);
  });

  it("collapses to the minimum when a corner is dragged past the opposite one, never inverting", () => {
    const crossed = resizeImageRect(RECT, "nw", 2, 2, W, H); // cruza la esquina fija
    expect(crossed.x0).toBeLessThanOrEqual(crossed.x1);
    expect(crossed.y0).toBeLessThanOrEqual(crossed.y1);
    expect((crossed.x1 - crossed.x0) * W).toBeGreaterThan(0);
    expect(pageAspect(crossed)).toBeCloseTo(pageAspect(RECT)); // sigue proporcional
  });

  it("grows and shrinks proportionally with the keyboard, clamped to a minimum", () => {
    const bigger = scaleImageRect(RECT, "se", 50, W, H);
    expect((bigger.x1 - bigger.x0) * W).toBeCloseTo((RECT.x1 - RECT.x0) * W + 50);
    expect(pageAspect(bigger)).toBeCloseTo(pageAspect(RECT));
    const tiny = scaleImageRect(RECT, "se", -10_000, W, H); // encoge más allá del mínimo
    expect((tiny.x1 - tiny.x0) * W).toBeGreaterThan(0);
    expect(pageAspect(tiny)).toBeCloseTo(pageAspect(RECT));
  });

  it.each([0.01, 0.5, 100])("fits aspect %s at page edges without changing proportions", (aspect) => {
    const placed = imageRect(0.99, 0.01, aspect, 600, 800);
    expect(placed.x0).toBeGreaterThanOrEqual(0);
    expect(placed.y0).toBeGreaterThanOrEqual(0);
    expect(placed.x1).toBeLessThanOrEqual(1);
    expect(placed.y1).toBeLessThanOrEqual(1);
    expect(((placed.x1 - placed.x0) * 600) / ((placed.y1 - placed.y0) * 800)).toBeCloseTo(aspect);
  });
});
