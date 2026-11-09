import { describe, expect, it } from "vitest";

import {
  buildInstructions,
  countPages,
  createPages,
  normalizeRotation,
  quarterTurnScale,
  rotatePages,
  togglePage,
} from "./pageEditor";

const previews = [1, 2, 3].map((number) => ({ number, width: 595, height: 842, thumbnail: "data:image/jpeg;base64,x" }));

describe("page editor", () => {
  it("normalizes accumulated rotations", () => {
    expect(normalizeRotation(-90)).toBe(270);
    expect(normalizeRotation(450)).toBe(90);
  });

  it("shrinks portrait pages turned sideways so they still fit", () => {
    expect(quarterTurnScale(595, 842)).toBeCloseTo(0.75, 2);
    expect(quarterTurnScale(842, 595)).toBe(1);
  });

  it("builds the final page list for each mode", () => {
    let pages = createPages(previews);
    pages = rotatePages(pages, -90, "p-3");
    pages = togglePage(pages, "p-2", "removed");
    pages = togglePage(pages, "p-3", "selected");
    const reordered = [pages[2]!, pages[0]!, pages[1]!];

    expect(buildInstructions("organize", reordered)).toEqual([
      { index: 2, rotation: 270 },
      { index: 0, rotation: 0 },
    ]);
    expect(buildInstructions("rotate", pages)).toEqual([
      { index: 0, rotation: 0 },
      { index: 1, rotation: 0 },
      { index: 2, rotation: 270 },
    ]);
    expect(buildInstructions("delete", pages)).toEqual([
      { index: 0, rotation: 0 },
      { index: 2, rotation: 0 },
    ]);
    expect(buildInstructions("extract", pages)).toEqual([{ index: 2, rotation: 0 }]);
    expect(countPages(pages)).toEqual({ total: 3, kept: 2, rotated: 1, selected: 1 });
  });
});
