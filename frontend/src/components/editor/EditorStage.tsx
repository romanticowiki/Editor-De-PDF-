import { type KeyboardEvent as ReactKeyboardEvent, type PointerEvent as ReactPointerEvent, type RefObject, memo, useEffect, useId, useLayoutEffect, useMemo, useRef, useState } from "react";

import { type ImageCorner, imageRect, moveImageRect, resizeImageRect, scaleImageRect } from "../../lib/editorGeometry";
import { newId } from "../../lib/id";
import { appendStrokePoint, finishStroke } from "../../lib/editorInput";
import type { EditorFormField, EditorPage } from "../../services/editorService";
import type { Annotation, EditorTool, FieldAnno, ImageAnno, NPoint, NRect, Rgb, SignatureAsset, TextEntry } from "./types";

interface EditorStageProps {
  page: EditorPage;
  pageIndex: number;
  tool: EditorTool;
  color: Rgb;
  fill: Rgb;
  size: number;
  strokeWidth: number;
  activeSignature: SignatureAsset | null;
  annotations: readonly Annotation[];
  onAdd: (annotation: Annotation) => void;
  onSetText: (id: string, text: string) => void;
  onDelete: (id: string) => void;
  onUpdateRect: (id: string, rect: NRect) => void;
  onSelectText: (id: string | null, size: number) => void;
  disabled: boolean;
  textInputRef: RefObject<TextEntry | null>;
}

interface ImageGesture {
  id: string;
  pointerId: number;
  start: [number, number];
  original: NRect;
  corner?: ImageCorner;
}

const CORNERS: readonly { corner: ImageCorner; label: string }[] = [
  { corner: "nw", label: "superior izquierda" },
  { corner: "ne", label: "superior derecha" },
  { corner: "sw", label: "inferior izquierda" },
  { corner: "se", label: "inferior derecha" },
];
const MIN_RECT = 0.01; // área mínima para no crear anotaciones por un clic accidental
const KEY_STEP_PT = 10; // paso de teclado "rápido", en puntos PDF
const KEY_STEP_FINE_PT = 1; // paso fino con Mayús, en puntos PDF

export function EditorStage({
  page,
  pageIndex,
  tool,
  color,
  fill,
  size,
  strokeWidth,
  activeSignature,
  annotations,
  onAdd,
  onSetText,
  onDelete,
  onUpdateRect,
  onSelectText,
  disabled,
  textInputRef,
}: EditorStageProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [rect, setRect] = useState<NRect | null>(null);
  const [stroke, setStroke] = useState<NPoint[] | null>(null);
  const strokeRef = useRef<{ pointerId: number; points: NPoint[] } | null>(null);
  const shapeRef = useRef<{ pointerId: number; start: NPoint; tool: EditorTool } | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const editingBackup = useRef<{ id: string; text: string } | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [imageDraft, setImageDraft] = useState<{ id: string; rect: NRect } | null>(null);
  const gesture = useRef<ImageGesture | null>(null);
  const instructionsId = useId();
  const fieldEdits = useMemo(() => {
    const edits = new Map<string, FieldAnno>();
    annotations.forEach((a) => { if (a.kind === "field") edits.set(a.name, a); });
    return edits;
  }, [annotations]);

  useEffect(() => {
    if (editingId) textInputRef.current?.focus({ preventScroll: true });
  }, [editingId, textInputRef]);

  const { width: W, height: H } = page;

  const at = (event: ReactPointerEvent): [number, number] => {
    const box = svgRef.current!.getBoundingClientRect();
    return [clamp((event.clientX - box.left) / box.width), clamp((event.clientY - box.top) / box.height)];
  };

  const handleDown = (event: ReactPointerEvent) => {
    if (disabled || editingId || !event.isPrimary || event.button !== 0 || gesture.current) return;
    setSelectedId(null);
    const [nx, ny] = at(event);

    const field = page.fields.find((candidate) => nx >= candidate.rect.x0 && nx <= candidate.rect.x1 && ny >= candidate.rect.y0 && ny <= candidate.rect.y1);
    if (field) {
      event.preventDefault();
      editField(field);
      return;
    }
    if (tool === "signature") {
      if (!activeSignature) return;
      const id = newId();
      onAdd({ id, kind: "image", page: pageIndex, rect: imageRect(nx, ny, activeSignature.aspect, W, H), imageIndex: activeSignature.index, previewUrl: activeSignature.previewUrl });
      setSelectedId(id);
      return;
    }
    svgRef.current?.setPointerCapture(event.pointerId);
    event.preventDefault();
    if (tool === "draw") {
      strokeRef.current = { pointerId: event.pointerId, points: [[nx, ny]] };
      setStroke(strokeRef.current.points);
    } else {
      shapeRef.current = { pointerId: event.pointerId, start: [nx, ny], tool };
      setRect({ x0: nx, y0: ny, x1: nx, y1: ny });
    }
  };

  const handleMove = (event: ReactPointerEvent) => {
    if (gesture.current) {
      if (event.pointerId !== gesture.current.pointerId) return;
      setImageDraft({ id: gesture.current.id, rect: gestureRect(event) });
    } else if (strokeRef.current?.pointerId === event.pointerId) {
      const screen = svgRef.current!.getBoundingClientRect();
      strokeRef.current.points = appendStrokePoint(strokeRef.current.points, at(event), screen.width, screen.height);
      setStroke(strokeRef.current.points);
    } else if (shapeRef.current?.pointerId === event.pointerId) {
      const [nx, ny] = at(event);
      setRect({ x0: shapeRef.current.start[0], y0: shapeRef.current.start[1], x1: nx, y1: ny });
    }
  };

  const handleUp = (event: ReactPointerEvent) => {
    if (gesture.current) {
      if (event.pointerId !== gesture.current.pointerId) return;
      const current = gesture.current;
      const updated = gestureRect(event);
      if (updated.x0 !== current.original.x0 || updated.y0 !== current.original.y0 || updated.x1 !== current.original.x1 || updated.y1 !== current.original.y1) {
        onUpdateRect(current.id, updated);
      }
      gesture.current = null;
      setImageDraft(null);
    } else if (strokeRef.current?.pointerId === event.pointerId) {
      const finished = finishStroke(strokeRef.current.points, at(event));
      if (finished.length > 1) onAdd({ id: newId(), kind: "draw", page: pageIndex, strokes: [finished], color, width: strokeWidth });
      strokeRef.current = null;
      setStroke(null);
    } else if (shapeRef.current?.pointerId === event.pointerId) {
      const shape = shapeRef.current;
      const [nx, ny] = at(event);
      const ordered = order({ x0: shape.start[0], y0: shape.start[1], x1: nx, y1: ny });
      const large = (ordered.x1 - ordered.x0) > MIN_RECT && (ordered.y1 - ordered.y0) > MIN_RECT;
      if (shape.tool === "text") {
        const id = newId();
        onAdd(large
          ? { id, kind: "textbox", page: pageIndex, rect: ordered, text: "", size, color }
          : { id, kind: "text", page: pageIndex, nx: shape.start[0], ny: shape.start[1], text: "", size, color });
        onSelectText(id, size);
        setEditingId(id);
      }
      if (large) {
        if (shape.tool === "highlight") {
          onAdd({ id: newId(), kind: "highlight", page: pageIndex, rect: ordered, color: [0.99, 0.85, 0.25] });
        } else if (shape.tool === "patch") {
          const id = newId();
          onAdd({ id, kind: "patch", page: pageIndex, rect: ordered, text: "", size, color, fill });
          onSelectText(id, size);
          setEditingId(id);
        }
      }
      shapeRef.current = null;
      setRect(null);
    }
    if (svgRef.current?.hasPointerCapture(event.pointerId)) svgRef.current.releasePointerCapture(event.pointerId);
  };

  const editField = (field: EditorFormField) => {
    if (disabled || field.readOnly || editingId) return;
    const previous = fieldEdits.get(field.name);
    const value = previous?.value ?? field.value;
    const id = newId();
    const fieldSize = Math.max(6, Math.min(40, previous?.size || field.size || 8));
    if (field.kind === "checkbox" || field.kind === "radio") {
      onSelectText(null, size);
      onAdd({ id, kind: "field", page: pageIndex, name: field.name, value: field.kind === "checkbox" ? !value : field.options[0] ?? "", size: fieldSize });
    } else {
      onAdd({ id, kind: "field", page: pageIndex, name: field.name, value: typeof value === "string" ? value : "", size: fieldSize });
      onSelectText(id, fieldSize);
      setEditingId(id);
    }
  };

  const beginImageGesture = (event: ReactPointerEvent<SVGGElement | HTMLButtonElement>, annotation: ImageAnno, corner?: ImageCorner) => {
    event.stopPropagation();
    if (disabled || editingId || !event.isPrimary || event.button !== 0 || gesture.current) return;
    event.preventDefault();
    event.currentTarget.focus();
    setSelectedId(annotation.id);
    gesture.current = { id: annotation.id, pointerId: event.pointerId, start: at(event), original: annotation.rect, corner };
    setImageDraft({ id: annotation.id, rect: annotation.rect });
    svgRef.current?.setPointerCapture(event.pointerId);
  };

  const gestureRect = (event: ReactPointerEvent): NRect => {
    const current = gesture.current!;
    const [x, y] = at(event);
    return current.corner
      ? resizeImageRect(current.original, current.corner,
        (current.corner.includes("w") ? current.original.x0 : current.original.x1) + x - current.start[0],
        (current.corner.includes("n") ? current.original.y0 : current.original.y1) + y - current.start[1],
        W, H)
      : moveImageRect(current.original, x - current.start[0], y - current.start[1]);
  };

  const cancelGesture = () => {
    const pointerId = gesture.current?.pointerId;
    gesture.current = null;
    setImageDraft(null);
    setRect(null);
    setStroke(null);
    strokeRef.current = null;
    shapeRef.current = null;
    if (pointerId !== undefined && svgRef.current?.hasPointerCapture(pointerId)) svgRef.current.releasePointerCapture(pointerId);
  };

  const imageKey = (event: ReactKeyboardEvent, annotation: ImageAnno, corner?: ImageCorner) => {
    if (disabled) return;
    if (event.key === "Escape") {
      cancelGesture();
      setSelectedId(null);
    } else if (event.key === "Enter" || event.key === " ") {
      setSelectedId(annotation.id);
    } else if (event.key === "Delete" || event.key === "Backspace") {
      cancelGesture();
      onDelete(annotation.id);
      setSelectedId(null);
    } else if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) {
      if (gesture.current) return;
      const stepPt = event.shiftKey ? KEY_STEP_FINE_PT : KEY_STEP_PT; // flechas = rápido; Mayús = fino
      if (corner) {
        // Sobre una esquina: redimensiona proporcional (→/↓ agrandan, ←/↑ encogen).
        const grow = event.key === "ArrowRight" || event.key === "ArrowDown";
        onUpdateRect(annotation.id, scaleImageRect(annotation.rect, corner, grow ? stepPt : -stepPt, W, H));
      } else {
        const dx = (event.key === "ArrowRight" ? stepPt : event.key === "ArrowLeft" ? -stepPt : 0) / W;
        const dy = (event.key === "ArrowDown" ? stepPt : event.key === "ArrowUp" ? -stepPt : 0) / H;
        onUpdateRect(annotation.id, moveImageRect(annotation.rect, dx, dy));
      }
    } else return;
    event.preventDefault();
    event.stopPropagation();
  };

  const commitText = (id: string, value: string) => {
    editingBackup.current = null;
    setEditingId(null);
    if (!value.trim() && annotations.find((a) => a.id === id)?.kind !== "field") onDelete(id);
    else onSetText(id, value);
  };

  const selected = annotations.find((a): a is ImageAnno => a.id === selectedId && a.kind === "image");
  const selectedRect = selected ? (imageDraft?.id === selected.id ? imageDraft.rect : selected.rect) : null;

  return (
    <div className="relative inline-block w-full select-none">
      <p id={instructionsId} className="sr-only">Flechas: mover la imagen (Mayús para ajuste fino). Sobre una esquina, las flechas redimensionan manteniendo la proporción. Supr: eliminar. Escape: cancelar movimiento.</p>
      <img src={page.image} alt={`Página ${page.number}`} className="block w-full rounded-[0.5rem]" draggable={false} />
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        className="absolute inset-0 size-full touch-none"
        style={{ cursor: disabled ? "wait" : imageDraft ? (gesture.current?.corner ? cornerCursor(gesture.current.corner) : "grabbing") : tool === "signature" && !activeSignature ? "not-allowed" : "crosshair" }}
        onPointerDown={handleDown}
        onPointerMove={handleMove}
        onPointerUp={handleUp}
        onPointerCancel={cancelGesture}
        onLostPointerCapture={cancelGesture}
      >
        {[...annotations.filter((a) => a.kind !== "image"), ...annotations.filter((a) => a.kind === "image")].map((annotation) => {
          if (annotation.kind === "field") return null;
          if (annotation.kind !== "image") return <g key={annotation.id}
            role={annotation.kind === "draw" || annotation.kind === "highlight" ? undefined : "button"}
            tabIndex={annotation.kind === "draw" || annotation.kind === "highlight" || disabled ? undefined : 0}
            aria-label={annotation.kind === "draw" || annotation.kind === "highlight" ? undefined : "Editar texto colocado"}
            onPointerDown={(event) => {
              if (annotation.kind === "draw" || annotation.kind === "highlight") return;
              event.stopPropagation();
              if (disabled || editingId) return;
              event.preventDefault();
              editingBackup.current = { id: annotation.id, text: annotation.text };
              onSelectText(annotation.id, annotation.size);
              setEditingId(annotation.id);
            }}
            onKeyDown={(event) => {
              if (annotation.kind !== "draw" && annotation.kind !== "highlight" && !disabled && (event.key === "Enter" || event.key === " ")) {
                event.preventDefault(); editingBackup.current = { id: annotation.id, text: annotation.text }; onSelectText(annotation.id, annotation.size); setEditingId(annotation.id);
              }
            }}><AnnotationShape annotation={annotation} width={W} height={H} /></g>;
          const displayed = imageDraft?.id === annotation.id ? { ...annotation, rect: imageDraft.rect } : annotation;
          return (
            <g
              key={annotation.id}
              role="button"
              tabIndex={disabled ? -1 : 0}
              aria-label={`Imagen ${annotation.imageIndex + 1}`}
              aria-pressed={selectedId === annotation.id}
              aria-describedby={instructionsId}
              onFocus={() => setSelectedId(annotation.id)}
              onPointerDown={(event) => beginImageGesture(event, annotation)}
              onKeyDown={(event) => imageKey(event, annotation)}
              style={{ cursor: disabled ? "wait" : imageDraft?.id === annotation.id ? "grabbing" : "grab" }}
            >
              <AnnotationShape annotation={displayed} width={W} height={H} />
              <rect {...box(displayed.rect, W, H)} fill="transparent" />
            </g>
          );
        })}
        {page.fields.map((field, index) => {
          const staged = fieldEdits.get(field.name);
          const value = staged?.value ?? field.value;
          return <g key={`${field.name}-${index}`} role={field.kind === "checkbox" || field.kind === "radio" ? "checkbox" : "button"}
            aria-label={`Campo: ${field.label}`} aria-checked={field.kind === "checkbox" ? value === true : field.kind === "radio" ? value === field.options[0] : undefined}
            aria-disabled={disabled || field.readOnly} tabIndex={disabled || field.readOnly ? -1 : 0}
            onPointerDown={(event) => { event.stopPropagation(); event.preventDefault(); editField(field); }}
            onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); editField(field); } }}
            style={{ cursor: field.readOnly ? "not-allowed" : "pointer" }}>
            {!field.readOnly && <NativeFieldShape field={field} value={value} size={staged?.size || field.size || 8} edited={!!staged} width={W} height={H} />}
            <rect {...box(field.rect, W, H)} fill="transparent" stroke={staged ? "var(--accent)" : "transparent"} strokeWidth={1} vectorEffect="non-scaling-stroke" />
          </g>;
        })}
        {selectedRect && <rect {...box(selectedRect, W, H)} fill="none" stroke="var(--accent)" strokeWidth={2} vectorEffect="non-scaling-stroke" pointerEvents="none" />}
        {rect && tool === "highlight" && <rect {...box(order(rect), W, H)} fill={css([0.99, 0.85, 0.25])} opacity={0.35} />}
        {rect && tool === "patch" && <rect {...box(order(rect), W, H)} fill={css(fill)} stroke={css(color)} strokeWidth={1} />}
        {rect && tool === "text" && <rect {...box(order(rect), W, H)} fill="none" stroke="var(--accent)" strokeWidth={1} vectorEffect="non-scaling-stroke" />}
        {stroke && (
          <polyline points={stroke.map(([x, y]) => `${x * W},${y * H}`).join(" ")} fill="none" stroke={css(color)} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" />
        )}
      </svg>

      {selected && selectedRect && CORNERS.map(({ corner, label }) => (
        <button
          key={corner}
          type="button"
          aria-label={`Redimensionar imagen: esquina ${label}`}
          aria-describedby={instructionsId}
          disabled={disabled}
          onPointerDown={(event) => beginImageGesture(event, selected, corner)}
          onKeyDown={(event) => imageKey(event, selected, corner)}
          className="absolute z-10 flex size-11 -translate-x-1/2 -translate-y-1/2 touch-none items-center justify-center rounded-full"
          style={{ left: `${(corner.includes("w") ? selectedRect.x0 : selectedRect.x1) * 100}%`, top: `${(corner.includes("n") ? selectedRect.y0 : selectedRect.y1) * 100}%`, cursor: cornerCursor(corner) }}
        >
          <span className="size-2.5 rounded-full border-2 border-accent bg-surface shadow-lift" />
        </button>
      ))}

      {editingId &&
        (() => {
          const target = annotations.find((a) => a.id === editingId);
          if (!target || target.kind === "image" || target.kind === "draw" || target.kind === "highlight") return null;
          const field = target.kind === "field" ? page.fields.find((f) => f.name === target.name) : null;
          const [ax, ay] = field ? [field.rect.x0, field.rect.y0] : anchor(target);
          const multiline = target.kind === "textbox" || target.kind === "patch" || field?.multiline;
          const attributes = {
              "data-annotation-id": target.id,
              autoFocus: true,
              "aria-label": field ? `Editar campo: ${field.label}` : target.kind === "patch" ? "Texto de la corrección" : target.kind === "textbox" ? "Texto de la caja" : "Texto de la anotación",
              disabled,
              value: target.kind === "field" ? String(target.value) : target.text,
              maxLength: 10_000,
              onChange: (event: React.ChangeEvent<TextEntry>) => onSetText(target.id, event.currentTarget.value),
              onBlur: (event: React.FocusEvent<TextEntry>) => commitText(target.id, event.currentTarget.value),
              onKeyDown: (event: ReactKeyboardEvent<TextEntry>) => {
                if (event.nativeEvent.isComposing) return;
                if (event.key === "Enter" && (!multiline || event.ctrlKey || event.metaKey)) { event.preventDefault(); event.currentTarget.blur(); }
                if (event.key === "Escape") {
                  event.preventDefault();
                  if (editingBackup.current?.id === target.id) onSetText(target.id, editingBackup.current.text);
                  else onDelete(target.id);
                  editingBackup.current = null;
                  setEditingId(null);
                }
              },
              className: "glass absolute z-10 min-h-11 rounded-control px-2 py-1 text-base text-ink [--glass-alpha:0.95]",
              style: { width: "min(16rem, 100%)", left: `clamp(0px, ${ax * 100}%, calc(100% - min(16rem, 100%)))`, top: `clamp(0px, ${ay * 100}%, calc(100% - 2.75rem))` },
          };
          if (field?.kind === "choice") return <select {...attributes} ref={(node) => { textInputRef.current = node; }}><option value="">Sin elegir</option>{field.options.map((option) => <option key={option} value={option}>{option}</option>)}</select>;
          return multiline
            ? <textarea {...attributes} ref={(node) => { textInputRef.current = node; }} placeholder="Escribe… Ctrl/⌘ + Enter confirma" rows={3} />
            : <input {...attributes} ref={(node) => { textInputRef.current = node; }} placeholder="Escribe…" />;
        })()}
    </div>
  );
}

const AnnotationShape = memo(function AnnotationShape({ annotation, width: W, height: H }: { annotation: Annotation; width: number; height: number }) {
  switch (annotation.kind) {
    case "text":
      return (
        <text x={annotation.nx * W} y={annotation.ny * H + annotation.size} fill={css(annotation.color)} fontSize={annotation.size} style={{ fontFamily: "EPDFEditor" }}>
          {annotation.text}
        </text>
      );
    case "highlight":
      return <rect {...box(annotation.rect, W, H)} fill={css(annotation.color)} opacity={0.35} />;
    case "patch":
      return (
        <>
          <rect {...box(annotation.rect, W, H)} fill={css(annotation.fill)} />
          <text x={annotation.rect.x0 * W} y={annotation.rect.y0 * H + annotation.size} fill={css(annotation.color)} fontSize={annotation.size} style={{ fontFamily: "EPDFEditor" }}>
            {annotation.text}
          </text>
        </>
      );
    case "draw":
      return (
        <>
          {annotation.strokes.map((points, index) => (
            <polyline key={index} points={points.map(([x, y]) => `${x * W},${y * H}`).join(" ")} fill="none" stroke={css(annotation.color)} strokeWidth={annotation.width} strokeLinecap="round" strokeLinejoin="round" />
          ))}
        </>
      );
    case "image":
      return <image href={annotation.previewUrl} {...box(annotation.rect, W, H)} preserveAspectRatio="xMidYMid meet" />;
    case "textbox":
      return <TextBoxShape rect={annotation.rect} text={annotation.text} size={annotation.size} color={annotation.color} width={W} height={H} />;
    case "field":
      return null;
  }
});

function TextBoxShape({ rect, text, size, color, width, height }: { rect: NRect; text: string; size: number; color: Rgb; width: number; height: number }) {
  const content = useRef<HTMLDivElement>(null);
  const [overflow, setOverflow] = useState(false);
  useLayoutEffect(() => {
    if (content.current) setOverflow(content.current.scrollHeight > content.current.clientHeight || content.current.scrollWidth > content.current.clientWidth);
  }, [text, size, rect, width, height]);
  return <>
    <foreignObject {...box(rect, width, height)} pointerEvents="none">
      <div ref={content} style={{ width: "100%", height: "100%", overflow: "hidden", whiteSpace: "pre-wrap", overflowWrap: "anywhere", paddingLeft: size * 0.2, fontFamily: "EPDFEditor", fontSize: size, lineHeight: 1.35, color: css(color) }}>{text}</div>
    </foreignObject>
    <rect {...box(rect, width, height)} fill="transparent" stroke={overflow ? "var(--danger)" : "var(--accent)"} strokeWidth={1} vectorEffect="non-scaling-stroke" aria-label={overflow ? "Texto desbordado: amplía la caja o reduce la fuente" : undefined} />
  </>;
}

function NativeFieldShape({ field, value, size, edited, width, height }: { field: EditorFormField; value: string | boolean; size: number; edited: boolean; width: number; height: number }) {
  const rect = field.rect;
  const b = box(rect, width, height);
  const checked = field.kind === "checkbox" ? value === true : value === field.options[0];
  return <>
    {field.kind === "checkbox" || field.kind === "radio"
      ? checked && (field.kind === "radio" ? <circle cx={b.x + b.width / 2} cy={b.y + b.height / 2} r={Math.min(b.width, b.height) * 0.25} fill="#000000" /> : <polyline points={`${b.x + b.width * 0.18},${b.y + b.height * 0.48} ${b.x + b.width * 0.4},${b.y + b.height * 0.72} ${b.x + b.width * 0.84},${b.y + b.height * 0.22}`} fill="none" stroke="#000000" strokeWidth={Math.min(1.05, b.width * 0.15)} strokeLinecap="round" strokeLinejoin="round" />)
      : <foreignObject {...b} pointerEvents="none"><div style={{ width: "100%", height: "100%", display: field.multiline ? "block" : "flex", alignItems: "center", overflow: "hidden", padding: 1, color: edited ? "#000000" : css(field.color ?? [0, 0, 0]), fontFamily: field.font.startsWith("Ti") ? "Times New Roman, serif" : field.font.startsWith("Cour") ? "Courier New, monospace" : "Arial, Helvetica, sans-serif", fontSize: size, lineHeight: 1.2, whiteSpace: field.multiline ? "pre-wrap" : "nowrap", overflowWrap: "anywhere" }}>{String(value)}</div></foreignObject>}
  </>;
}

function box(rect: NRect, W: number, H: number) {
  return { x: rect.x0 * W, y: rect.y0 * H, width: (rect.x1 - rect.x0) * W, height: (rect.y1 - rect.y0) * H };
}

function anchor(annotation: Annotation): [number, number] {
  if (annotation.kind === "text") return [annotation.nx, annotation.ny];
  if (annotation.kind === "patch" || annotation.kind === "textbox") return [annotation.rect.x0, annotation.rect.y0];
  return [0, 0];
}

function order(rect: NRect): NRect {
  return { x0: Math.min(rect.x0, rect.x1), y0: Math.min(rect.y0, rect.y1), x1: Math.max(rect.x0, rect.x1), y1: Math.max(rect.y0, rect.y1) };
}

function css([r, g, b]: Rgb): string {
  return `rgb(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)})`;
}

function clamp(value: number): number {
  return Math.min(Math.max(value, 0), 1);
}

function cornerCursor(corner: ImageCorner): string {
  return corner === "nw" || corner === "se" ? "nwse-resize" : "nesw-resize";
}
