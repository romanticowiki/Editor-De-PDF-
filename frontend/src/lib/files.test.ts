import { describe, expect, it } from "vitest";

import { formatBytes, partitionFiles } from "./files";

const pdfLimits = { maxFiles: 2, maxFileBytes: 10, accept: { extensions: [".pdf"], label: "un PDF" } };

function pdf(name: string, size = 5): File {
  return new File([new Uint8Array(size)], name, { type: "application/pdf", lastModified: 1 });
}

describe("partitionFiles", () => {
  it("accepts valid files", () => {
    const { accepted, rejected } = partitionFiles([], [pdf("a.pdf"), pdf("b.pdf")], pdfLimits);

    expect(accepted.map((file) => file.name)).toEqual(["a.pdf", "b.pdf"]);
    expect(rejected).toEqual([]);
  });

  it("rejects with a precise reason", () => {
    const existing = [pdf("a.pdf")];
    const incoming = [
      new File(["x"], "notes.txt", { type: "text/plain" }),
      pdf("empty.pdf", 0),
      pdf("huge.pdf", 11),
      pdf("a.pdf"),
      pdf("b.pdf"),
      pdf("c.pdf"),
    ];

    const { accepted, rejected } = partitionFiles(existing, incoming, pdfLimits);

    expect(accepted.map((file) => file.name)).toEqual(["b.pdf"]);
    expect(rejected.map((rejection) => rejection.reason)).toEqual([
      "wrong_type",
      "empty",
      "too_large",
      "duplicate",
      "limit_reached",
    ]);
  });

  it("matches extensions case-insensitively and PDFs by MIME type", () => {
    const wordLimits = { maxFiles: 5, maxFileBytes: 10, accept: { extensions: [".docx", ".doc"], label: "un Word" } };

    expect(partitionFiles([], [new File(["x"], "CARTA.DOCX")], wordLimits).accepted).toHaveLength(1);
    expect(partitionFiles([], [new File(["%PDF-"], "descarga", { type: "application/pdf" })], pdfLimits).accepted).toHaveLength(1);
    expect(partitionFiles([], [new File(["x"], "carta.pdf")], wordLimits).rejected[0]?.reason).toBe("wrong_type");
  });
});

describe("formatBytes", () => {
  it("uses readable units", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(1536)).toBe("1,5 KB");
    expect(formatBytes(5 * 1024 * 1024)).toBe("5 MB");
  });
});
