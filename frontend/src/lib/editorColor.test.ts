import { describe, expect, it } from "vitest";

import { hexToRgb, rgbToHex } from "./editorColor";

describe("editor colors", () => {
  it("converts screen and color input hex values to normalized PDF RGB", () => {
    expect(hexToRgb("#000000")).toEqual([0, 0, 0]);
    expect(hexToRgb("#FFFFFF")).toEqual([1, 1, 1]);
    expect(hexToRgb("#a0522d")).toEqual([160 / 255, 82 / 255, 45 / 255]);
  });

  it("shows the selected PDF RGB color as a full native color input value", () => {
    expect(rgbToHex([0.63, 0.32, 0.18])).toBe("#a1522e");
    expect(rgbToHex(hexToRgb("#017ffe"))).toBe("#017ffe");
  });

  it("rejects malformed values instead of quietly converting them to black", () => {
    expect(() => hexToRgb("#abc")).toThrow();
    expect(() => hexToRgb("#zzzzzz")).toThrow();
  });
});
