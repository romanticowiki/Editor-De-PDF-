import { afterEach, describe, expect, it, vi } from "vitest";

import { API_ERROR_COPY } from "../copy/messages";
import { filenameFromDisposition, requestFile, requestJson } from "./apiClient";

function jsonResponse(body: unknown, init: ResponseInit): Response {
  return new Response(JSON.stringify(body), { ...init, headers: { "Content-Type": "application/json", ...init.headers } });
}

const identity = (data: unknown) => data;

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("apiClient", () => {
  it("maps 429 to rate_limited with Retry-After", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "Espera." }, { status: 429, headers: { "Retry-After": "7" } })));

    await expect(requestJson("/x", identity)).rejects.toMatchObject({ kind: "rate_limited", status: 429, retryAfterSeconds: 7 });
  });

  it("shows the backend detail for 4xx", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "«a.pdf» no es un PDF." }, { status: 415 })));

    await expect(requestJson("/x", identity)).rejects.toMatchObject({ kind: "client", message: "«a.pdf» no es un PDF." });
  });

  it("never leaks server internals on 500", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "Traceback…" }, { status: 500 })));

    await expect(requestJson("/x", identity)).rejects.toMatchObject({ kind: "server", message: API_ERROR_COPY.server });
  });

  it("shows the guidance of 503 and 504", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "Necesitas Office." }, { status: 503 })));
    await expect(requestJson("/x", identity)).rejects.toMatchObject({ kind: "server", message: "Necesitas Office." });

    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "Tarda demasiado." }, { status: 504 })));
    await expect(requestJson("/x", identity)).rejects.toMatchObject({ kind: "timeout", message: "Tarda demasiado." });
  });

  it("maps a failed fetch to network", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await expect(requestJson("/x", identity)).rejects.toMatchObject({ kind: "network" });
  });

  it("maps a caller abort to aborted", async () => {
    const controller = new AbortController();
    controller.abort();
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new DOMException("Aborted", "AbortError")));

    await expect(requestJson("/x", identity, { signal: controller.signal })).rejects.toMatchObject({ kind: "aborted" });
  });

  it("returns the file, its name and the reported sizes", async () => {
    const response = new Response(new Blob(["%PDF-"]), {
      status: 200,
      headers: {
        "Content-Disposition": "attachment; filename=\"cancion.pdf\"; filename*=UTF-8''canci%C3%B3n.pdf",
        "X-Original-Size": "2048",
        "X-Result-Size": "512",
      },
    });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));

    const download = await requestFile("/compress", "fallback.pdf", { method: "POST" });

    expect(download).toMatchObject({ filename: "canción.pdf", originalBytes: 2048, resultBytes: 512 });
    expect(download.blob.size).toBe(5);
  });
});

describe("filenameFromDisposition", () => {
  it("prefers the RFC 5987 name and falls back to the plain one", () => {
    expect(filenameFromDisposition('attachment; filename="a b.pdf"')).toBe("a b.pdf");
    expect(filenameFromDisposition("attachment; filename*=UTF-8''uni%C3%B3n.pdf")).toBe("unión.pdf");
    expect(filenameFromDisposition("attachment; filename=\"x.pdf\"; filename*=UTF-8''%E0%A4%A")).toBe("x.pdf");
    expect(filenameFromDisposition(null)).toBeNull();
  });
});
