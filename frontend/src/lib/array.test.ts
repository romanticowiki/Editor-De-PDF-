import { describe, expect, it } from "vitest";

import { moveItem } from "./array";

describe("moveItem", () => {
  it("moves an item to a new index without mutating", () => {
    const list = ["a", "b", "c"];

    expect(moveItem(list, 0, 2)).toEqual(["b", "c", "a"]);
    expect(list).toEqual(["a", "b", "c"]);
  });

  it("returns the same reference for invalid moves", () => {
    const list = ["a", "b"];

    expect(moveItem(list, 0, -1)).toBe(list);
    expect(moveItem(list, 1, 2)).toBe(list);
    expect(moveItem(list, -1, 0)).toBe(list);
  });
});
