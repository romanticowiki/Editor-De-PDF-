import { describe, expect, it } from "vitest";

import { TOOLS, filterTools, findToolBySlug, groupByCategory, missingEngine } from "./catalog";

describe("tool catalog", () => {
  it("has unique ids and URL-safe unique slugs", () => {
    expect(new Set(TOOLS.map((tool) => tool.id)).size).toBe(TOOLS.length);
    expect(new Set(TOOLS.map((tool) => tool.slug)).size).toBe(TOOLS.length);
    for (const tool of TOOLS) expect(tool.slug).toMatch(/^[a-z0-9-]+$/);
  });

  it("declares valid endpoints, extensions and defaults", () => {
    for (const tool of TOOLS) {
      if (tool.kind !== "file" && tool.kind !== "multi") continue;
      expect(tool.endpoint.startsWith("/")).toBe(true);
      for (const extension of tool.accept.extensions) expect(extension).toMatch(/^\.[a-z]+$/);

      const names = (tool.fields ?? []).map((field) => field.name);
      expect(new Set(names).size).toBe(names.length);
      for (const field of tool.fields ?? []) {
        if (field.kind === "choice") expect(field.options.map((option) => option.value)).toContain(field.defaultValue);
        if (field.visibleWhen) expect(names).toContain(field.visibleWhen.field);
      }
    }
  });

  it("searches without caring about accents or case", () => {
    const titles = (query: string) => filterTools(TOOLS, query).map((tool) => tool.title);

    expect(titles("tamano")).toContain("Comprimir PDF");
    expect(titles("excel")).toEqual(expect.arrayContaining(["PDF a Excel", "Excel a PDF"]));
    expect(titles("rotar")).toEqual(["Girar PDF"]);
    expect(titles("markdown")).toEqual(
      expect.arrayContaining(["Markdown a PDF", "Markdown a Word", "Markdown a PowerPoint"]),
    );
  });

  it("groups tools in the display order", () => {
    expect(groupByCategory(TOOLS).map((group) => group.category.id)).toEqual([
      "organize",
      "optimize",
      "from-pdf",
      "to-pdf",
      "edit",
      "ai",
    ]);
  });

  it("only flags an engine as missing when the backend confirmed it", () => {
    const ocr = findToolBySlug("ocr-pdf");
    if (!ocr) throw new Error("ocr-pdf debería existir");

    expect(missingEngine(ocr, {})).toBeNull();
    expect(missingEngine(ocr, { ocr: true })).toBeNull();
    expect(missingEngine(ocr, { ocr: false })).toBe("ocr");
  });

  it("requires external-service consent for translation and keeps partial Word opt-in", () => {
    const translate = findToolBySlug("traducir-pdf");
    const word = findToolBySlug("pdf-a-word");
    if (translate?.kind !== "file" || word?.kind !== "file") throw new Error("Faltan herramientas de conversión");

    expect(translate.fields?.find((field) => field.name === "consent")).toMatchObject({
      kind: "checkbox",
      required: true,
      defaultValue: "false",
    });
    expect(word.fields?.find((field) => field.name === "allow_partial")).toMatchObject({
      kind: "checkbox",
      required: false,
      defaultValue: "false",
    });
  });
});
