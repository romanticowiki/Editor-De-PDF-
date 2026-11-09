import { describe, expect, it } from "vitest";

import { appendStrokePoint, finishStroke, editorNumber } from "./editorInput";

describe("editor input", () => {
  it("keeps a sub-point gesture final coordinate even without pointermove", () => {
    expect(finishStroke([[0.1, 0.1]], [0.1001, 0.1002])).toEqual([[0.1, 0.1], [0.1001, 0.1002]]);
    expect(finishStroke([[0.1, 0.1]], [0.1, 0.1])).toEqual([]);
  });

  it("samples tiny marks according to visible pixels at 100% and 200%", () => {
    for (const scale of [1, 2]) {
      expect(appendStrokePoint([[0.1, 0.1]], [0.1005, 0.1005], 792 * scale, 612 * scale)).toHaveLength(2);
    }
  });

  it("reserves the final endpoint when a stroke reaches the API point limit", () => {
    const points = Array.from({ length: 3000 }, () => [0.1, 0.1] as [number, number]);
    const finished = finishStroke(points, [0.2, 0.3]);
    expect(finished).toHaveLength(3000);
    expect(finished.at(-1)).toEqual([0.2, 0.3]);
  });

  it("accepts precise font sizes and rejects blanks or invalid steps", () => {
    expect(editorNumber("6.5", 6, 40, 0.5)).toBe(6.5);
    expect(editorNumber("8", 6, 40, 0.5)).toBe(8);
    for (const input of ["", "5", "41", "8.1", "NaN"]) expect(editorNumber(input, 6, 40, 0.5)).toBeNull();
    expect(editorNumber("1.25", 0.5, 20, 0.25)).toBe(1.25);
  });
});
