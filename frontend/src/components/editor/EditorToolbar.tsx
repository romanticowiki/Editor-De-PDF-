import { Eraser, Highlighter, Image, Loader2, Pencil, Pipette, Save, Type, Undo2, Upload } from "lucide-react";
import type { ComponentType } from "react";
import { useEffect, useId, useRef, useState } from "react";

import { cx } from "../../lib/cx";
import { hexToRgb, rgbToHex } from "../../lib/editorColor";
import { editorNumber } from "../../lib/editorInput";
import type { EditorTool, Rgb, SignatureAsset } from "./types";

const PALETTE: readonly { name: string; rgb: Rgb }[] = [
  { name: "Tinta", rgb: [0.15, 0.14, 0.12] },
  { name: "Terracota", rgb: [0.63, 0.32, 0.18] },
  { name: "Teal", rgb: [0.24, 0.42, 0.42] },
  { name: "Rojo", rgb: [0.78, 0.22, 0.18] },
];

const SIZES = [6.5, 8, 10, 12, 16, 22] as const;

const TOOLS: readonly { id: EditorTool; label: string; icon: ComponentType<{ className?: string }>; hint: string }[] = [
  { id: "text", label: "Texto", icon: Type, hint: "Clic para texto de punto; arrastra para una caja multilínea" },
  { id: "highlight", label: "Resaltar", icon: Highlighter, hint: "Arrastra sobre el texto" },
  { id: "draw", label: "Dibujar", icon: Pencil, hint: "Traza a mano alzada" },
  { id: "patch", label: "Corregir", icon: Eraser, hint: "Tapa y reescribe" },
  { id: "signature", label: "Imagen/Sticker", icon: Image, hint: "Sube un PNG o JPG, arrástralo y ajusta su tamaño" },
];

const COLOR_TOOLS: ReadonlySet<EditorTool> = new Set(["text", "draw", "patch"]);
const SIZE_TOOLS: ReadonlySet<EditorTool> = new Set(["text", "patch"]);

interface EditorToolbarProps {
  tool: EditorTool;
  onTool: (tool: EditorTool) => void;
  color: Rgb;
  onColor: (color: Rgb) => void;
  fill: Rgb;
  onFill: (color: Rgb) => void;
  size: number;
  onSize: (size: number) => void;
  strokeWidth: number;
  onStrokeWidth: (width: number) => void;
  fieldSelected: boolean;
  signatures: readonly SignatureAsset[];
  activeSignature: number | null;
  onUploadSignature: (file: File) => void;
  onActiveSignature: (index: number) => void;
  changeCount: number;
  onUndo: () => void;
  onSave: () => void;
  isSaving: boolean;
  isUploading: boolean;
}

export function EditorToolbar({
  tool,
  onTool,
  color,
  onColor,
  fill,
  onFill,
  size,
  onSize,
  strokeWidth,
  onStrokeWidth,
  fieldSelected,
  signatures,
  activeSignature,
  onUploadSignature,
  onActiveSignature,
  changeCount,
  onUndo,
  onSave,
  isSaving,
  isUploading,
}: EditorToolbarProps) {
  const fileInput = useRef<HTMLInputElement>(null);
  const groupId = useId();

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-5">
      <div className="min-h-0 flex-1 overflow-y-auto">
      <fieldset disabled={isSaving} className="space-y-3">
        <section>
          <p className="mb-2 text-[0.75rem] font-bold tracking-[0.12em] text-muted uppercase">Herramienta</p>
          <div className="grid grid-cols-2 gap-2">
            {TOOLS.map(({ id, label, icon: Icon, hint }) => (
              <button
                key={id}
                type="button"
                onClick={() => onTool(id)}
                title={hint}
                aria-pressed={tool === id}
                className={cx(
                  "flex items-center gap-2 rounded-control border px-3 py-2.5 text-left text-[0.875rem] font-semibold transition-colors duration-150",
                  tool === id
                    ? "border-accent bg-accent-soft text-accent"
                    : "border-subtle text-ink-soft hover:border-strong hover:text-ink",
                )}
              >
                <Icon className="size-4 shrink-0" />
                {label}
              </button>
            ))}
          </div>
        </section>

        {fieldSelected && <p className="text-sm text-muted">El texto de los campos se guarda en negro puro y sigue editable.</p>}

        {COLOR_TOOLS.has(tool) && !fieldSelected && (
          <ColorControl key={tool} label={tool === "draw" ? "Trazo" : "Texto"} color={color} onColor={onColor} disabled={isSaving} palette />
        )}

        {tool === "patch" && (
          <ColorControl label="Fondo" color={fill} onColor={onFill} disabled={isSaving} />
        )}

        {(SIZE_TOOLS.has(tool) || fieldSelected) && (
          <section>
            <label htmlFor={groupId} className="mb-2 block text-[0.75rem] font-bold tracking-[0.12em] text-muted uppercase">Tamaño de fuente (pt)</label>
            <input id={groupId} type="number" min={6} max={40} step={0.5} value={size} onChange={(event) => {
              const next = editorNumber(event.currentTarget.value, 6, 40, 0.5);
              if (next !== null) onSize(next);
            }} onBlur={(event) => { if (!event.currentTarget.validity.valid || !event.currentTarget.value) event.currentTarget.value = String(size); }} className="min-h-11 w-full rounded-control border border-subtle bg-surface px-3 text-base text-ink" />
            <div className="mt-2 flex flex-wrap gap-1" role="group" aria-label="Tamaños rápidos">
              {SIZES.map((value) => (
                <button
                  key={value}
                  type="button"
                  aria-label={`${value} pt`}
                  aria-pressed={size === value}
                  onClick={() => onSize(value)}
                  className={cx(
                    "min-h-11 min-w-11 rounded-control border px-2 text-sm font-semibold transition-colors duration-150",
                    size === value
                      ? "border-accent bg-accent-soft text-accent"
                      : "border-subtle text-ink-soft hover:border-strong hover:text-ink",
                  )}
                >
                  {value}
                </button>
              ))}
            </div>
          </section>
        )}

        {tool === "draw" && <section>
          <label htmlFor={`${groupId}-stroke`} className="mb-2 block text-xs font-bold text-muted uppercase">Grosor del trazo (pt)</label>
          <input id={`${groupId}-stroke`} type="number" min={0.5} max={20} step={0.25} value={strokeWidth} onChange={(event) => {
            const next = editorNumber(event.currentTarget.value, 0.5, 20, 0.25);
            if (next !== null) onStrokeWidth(next);
          }} onBlur={(event) => { if (!event.currentTarget.validity.valid || !event.currentTarget.value) event.currentTarget.value = String(strokeWidth); }} className="min-h-11 w-full rounded-control border border-subtle bg-surface px-3 text-base text-ink" />
        </section>}

        {tool === "text" && <p className="text-sm leading-snug text-muted">Clic para escribir. Arrastra una caja para texto multilínea. Ctrl/⌘ + Enter confirma; Escape cancela. Puedes volver a tocar un texto para editarlo.</p>}

        {tool === "signature" && (
          <section>
            <p className="mb-2 text-[0.75rem] font-bold tracking-[0.12em] text-muted uppercase">Imagen, firma o sello</p>
            <button
              type="button"
              onClick={() => fileInput.current?.click()}
              disabled={isUploading}
              className="flex w-full items-center justify-center gap-2 rounded-control border border-dashed border-strong py-2.5 text-[0.875rem] font-semibold text-ink-soft transition-colors duration-150 hover:border-accent hover:text-accent"
            >
              {isUploading ? <Loader2 className="size-4 animate-spin" /> : <Upload className="size-4" />}
              {isUploading ? "Cargando imagen…" : "Subir imagen"}
            </button>
            <input
              ref={fileInput}
              type="file"
              accept="image/png,image/jpeg"
              aria-label="Subir imagen PNG o JPG"
              className="sr-only"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) onUploadSignature(file);
                event.target.value = "";
              }}
            />
            {signatures.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {signatures.map((asset) => (
                  <button
                    key={asset.index}
                    type="button"
                    onClick={() => onActiveSignature(asset.index)}
                    aria-pressed={activeSignature === asset.index}
                    className={cx(
                      "flex h-12 w-16 items-center justify-center rounded-control border bg-surface-sunken p-1 transition-colors",
                      activeSignature === asset.index ? "border-accent" : "border-subtle hover:border-strong",
                    )}
                  >
                    <img src={asset.previewUrl} alt={`Imagen ${asset.index + 1}`} className="max-h-full max-w-full object-contain" />
                  </button>
                ))}
              </div>
            )}
            <p className="mt-2 text-[0.8125rem] leading-snug text-muted">
              Sube una imagen PNG o JPG (hasta 5 MB). Aparece en el centro; arrástrala y ajusta las esquinas. Haz clic en la página para colocar otra copia.
            </p>
            <p className="mt-2 text-[0.8125rem] leading-snug text-muted">Con teclado: Tab para seleccionar, flechas para mover (Mayús = ajuste fino), Tab hasta una esquina y flechas para cambiar el tamaño, y Supr para eliminar.</p>
          </section>
        )}
      </fieldset>
      </div>

      <div className="shrink-0 space-y-2 border-t border-subtle pt-4">
        <button
          type="button"
          onClick={onUndo}
          disabled={changeCount === 0 || isSaving || isUploading}
          className="flex w-full items-center justify-center gap-2 rounded-control py-2 text-[0.875rem] font-semibold text-ink-soft transition-colors duration-150 hover:text-ink disabled:opacity-40"
        >
          <Undo2 className="size-4" />
          Deshacer
        </button>
        <button
          type="button"
          onClick={onSave}
          disabled={changeCount === 0 || isSaving || isUploading}
          className="flex w-full items-center justify-center gap-2 rounded-control bg-accent py-3 text-[0.9375rem] font-bold text-on-accent shadow-lift transition-colors duration-150 hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSaving ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />}
          Guardar y descargar
        </button>
        <p className="text-center text-[0.8125rem] text-muted">
          {changeCount === 0 ? "Sin cambios todavía." : `${changeCount} ${changeCount === 1 ? "cambio" : "cambios"} por guardar.`}
        </p>
      </div>
    </div>
  );
}

function ColorControl({ label, color, onColor, disabled, palette = false }: {
  label: string;
  color: Rgb;
  onColor: (color: Rgb) => void;
  disabled: boolean;
  palette?: boolean;
}) {
  const picker = useRef<AbortController | null>(null);
  const [isPicking, setIsPicking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const labelId = useId();
  const hex = rgbToHex(color);

  useEffect(() => () => {
    const activePicker = picker.current;
    picker.current = null;
    activePicker?.abort();
  }, []);

  useEffect(() => {
    if (disabled) picker.current?.abort();
  }, [disabled]);

  async function pickColor() {
    if (!window.EyeDropper || picker.current) return;
    const controller = new AbortController();
    picker.current = controller;
    setIsPicking(true);
    setError(null);
    try {
      const { sRGBHex } = await new window.EyeDropper().open({ signal: controller.signal });
      if (!controller.signal.aborted) onColor(hexToRgb(sRGBHex));
    } catch (cause) {
      if (!controller.signal.aborted && !(cause instanceof DOMException && cause.name === "AbortError")) {
        setError("No se pudo tomar el color. Usa el selector o vuelve a intentarlo.");
      }
    } finally {
      if (picker.current === controller) {
        picker.current = null;
        setIsPicking(false);
      }
    }
  }

  return (
    <section aria-labelledby={labelId}>
      <div className="mb-2 flex items-center justify-between gap-2">
        <p id={labelId} className="text-[0.75rem] font-bold tracking-[0.12em] text-muted uppercase">{label}</p>
        <output aria-live="polite" aria-label={`Color elegido de ${label.toLowerCase()}`} className="text-[0.75rem] font-semibold text-muted tabular-nums">{hex.toUpperCase()}</output>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {palette && PALETTE.map((swatch) => (
          <button
            key={swatch.name}
            type="button"
            title={swatch.name}
            aria-label={`${label}: ${swatch.name}`}
            aria-pressed={sameColor(color, swatch.rgb)}
            disabled={isPicking}
            onClick={() => { setError(null); onColor(swatch.rgb); }}
            className="flex size-10 cursor-pointer items-center justify-center rounded-control transition-colors duration-150 hover:bg-surface-sunken disabled:cursor-wait disabled:opacity-50"
          >
            <span
              className={cx(
                // Borde siempre visible: el swatch oscuro «Tinta» no desaparece en modo oscuro.
                "size-7 rounded-full border border-subtle ring-2 ring-offset-2 ring-offset-surface",
                sameColor(color, swatch.rgb) ? "ring-accent-ring" : "ring-transparent",
              )}
              style={{ backgroundColor: rgbToHex(swatch.rgb) }}
            />
          </button>
        ))}
        <input
          type="color"
          value={hex}
          aria-label={`Color personalizado de ${label.toLowerCase()}`}
          disabled={isPicking}
          onInput={(event) => { setError(null); onColor(hexToRgb(event.currentTarget.value)); }}
          className="size-10 shrink-0 cursor-pointer rounded-control border border-subtle bg-surface p-1 disabled:cursor-wait disabled:opacity-50"
        />
        {typeof window.EyeDropper === "function" && (
          <button
            type="button"
            onClick={() => void pickColor()}
            aria-label={`Cuentagotas para ${label.toLowerCase()}`}
            title={`Tomar el color de ${label.toLowerCase()} de la pantalla`}
            aria-busy={isPicking}
            disabled={isPicking}
            className="flex size-10 shrink-0 cursor-pointer items-center justify-center rounded-control border border-subtle text-ink-soft transition-colors duration-150 hover:border-accent hover:text-accent disabled:cursor-wait disabled:opacity-50"
          >
            {isPicking ? <Loader2 className="size-4 animate-spin" /> : <Pipette className="size-4" />}
          </button>
        )}
      </div>
      {error && <p role="alert" className="mt-2 text-[0.8125rem] leading-snug text-danger">{error}</p>}
    </section>
  );
}

function sameColor(a: Rgb, b: Rgb): boolean {
  return a[0] === b[0] && a[1] === b[1] && a[2] === b[2];
}
