import { describe, expect, it } from "vitest";

import type { ToolField } from "../tools/types";
import { applyFieldChange, excludedOption, firstFieldError, initialFieldValues, submittableFields } from "./fields";

const LANGS = [
  { value: "es", label: "Español", description: "" },
  { value: "en", label: "Inglés", description: "" },
  { value: "fr", label: "Francés", description: "" },
];

const LANGUAGE_FIELDS: readonly ToolField[] = [
  { kind: "choice", name: "source_lang", label: "Origen", defaultValue: "es", options: LANGS },
  { kind: "choice", name: "target_lang", label: "Destino", defaultValue: "en", distinctFrom: "source_lang", options: LANGS },
];

const FIELDS: readonly ToolField[] = [
  {
    kind: "choice",
    name: "mode",
    label: "Modo",
    defaultValue: "pages",
    options: [
      { value: "pages", label: "Páginas", description: "" },
      { value: "ranges", label: "Rangos", description: "" },
    ],
  },
  {
    kind: "text",
    name: "ranges",
    label: "Rangos",
    defaultValue: "",
    maxLength: 100,
    required: true,
    visibleWhen: { field: "mode", equals: "ranges" },
    validate: (value) => (/^[\d\s,-]+$/.test(value) ? null : "Formato no válido."),
  },
];

const CONSENT: ToolField = {
  kind: "checkbox",
  name: "consent",
  label: "Acepto enviar el texto",
  description: "El contenido se enviará a Groq.",
  defaultValue: "false",
  required: true,
  requiredMessage: "Debes aceptar antes de continuar.",
};

describe("tool fields", () => {
  it("starts from the defaults", () => {
    expect(initialFieldValues(FIELDS)).toEqual({ mode: "pages", ranges: "" });
  });

  it("ignores hidden fields when validating and submitting", () => {
    const values = { mode: "pages", ranges: "basura" };

    expect(firstFieldError(FIELDS, values)).toBeNull();
    expect(submittableFields(FIELDS, values, { target: "pdf" })).toEqual({ target: "pdf", mode: "pages" });
  });

  it("validates visible fields and trims what it sends", () => {
    expect(firstFieldError(FIELDS, { mode: "ranges", ranges: "  " })).toBe("Completa este campo para continuar.");
    expect(firstFieldError(FIELDS, { mode: "ranges", ranges: "1-a" })).toBe("Formato no válido.");
    expect(submittableFields(FIELDS, { mode: "ranges", ranges: " 1-3 " })).toEqual({ mode: "ranges", ranges: "1-3" });
  });

  it("requires explicit consent and submits it only after selection", () => {
    expect(firstFieldError([CONSENT], { consent: "false" })).toBe("Debes aceptar antes de continuar.");
    expect(submittableFields([CONSENT], { consent: "true" })).toEqual({ consent: "true" });
  });

  it("keeps source and target languages distinct", () => {
    const values = { source_lang: "es", target_lang: "en" };

    // Cambiar el origen al valor que tenía el destino empuja el destino a otro idioma.
    const next = applyFieldChange(LANGUAGE_FIELDS, values, "source_lang", "en");
    expect(next.source_lang).toBe("en");
    expect(next.target_lang).not.toBe("en");

    // Un cambio de destino que no choca se respeta tal cual.
    expect(applyFieldChange(LANGUAGE_FIELDS, values, "target_lang", "fr")).toEqual({
      source_lang: "es",
      target_lang: "fr",
    });
  });

  it("hides the counterpart's language from the destination options", () => {
    const [source, target] = LANGUAGE_FIELDS;
    expect(excludedOption(target!, { source_lang: "fr", target_lang: "en" })).toBe("fr");
    expect(excludedOption(source!, { source_lang: "fr", target_lang: "en" })).toBeUndefined();
  });
});
