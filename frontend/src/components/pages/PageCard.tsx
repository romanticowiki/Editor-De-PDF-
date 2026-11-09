import type { DraggableAttributes, DraggableSyntheticListeners } from "@dnd-kit/core";
import { Check, RotateCcw, RotateCw, Trash2, Undo2 } from "lucide-react";
import { motion } from "motion/react";

import { cx } from "../../lib/cx";
import { springs } from "../../lib/motion";
import { type EditablePage, isQuarterTurn, normalizeRotation, quarterTurnScale } from "../../lib/pageEditor";
import type { PageEditorMode } from "../../tools/types";
import { IconButton } from "../ui/IconButton";

export interface DragHandle {
  ref: (element: HTMLElement | null) => void;
  attributes: DraggableAttributes;
  listeners: DraggableSyntheticListeners;
}

interface PageCardProps {
  page: EditablePage;
  position: number;
  mode: PageEditorMode;
  disabled: boolean;
  onActivate: (id: string) => void;
  onRotate: (id: string, delta: 90 | -90) => void;
  onToggleRemoved: (id: string) => void;
  dragHandle?: DragHandle;
  isDragging?: boolean;
}

const ACTIVATE_LABEL: Record<Exclude<PageEditorMode, "organize">, (page: string) => string> = {
  rotate: (page) => `Girar ${page} 90°`,
  delete: (page) => `Eliminar ${page}`,
  extract: (page) => `Extraer ${page}`,
};

export function PageCard({
  page,
  position,
  mode,
  disabled,
  onActivate,
  onRotate,
  onToggleRemoved,
  dragHandle,
  isDragging = false,
}: PageCardProps) {
  const pageName = `página ${page.index + 1}`;
  const rotation = normalizeRotation(page.angle);
  const scale = isQuarterTurn(page.angle) ? quarterTurnScale(page.width, page.height) : 1;
  const isSelected = mode === "extract" && page.selected;

  const frame = cx(
    "group relative flex aspect-[3/4] w-full items-center justify-center overflow-hidden rounded-[0.75rem] border-[1.5px] bg-surface transition-[border-color,box-shadow] duration-150 ease-out-quart",
    page.removed && "border-danger",
    isSelected && "border-accent-ring shadow-[0_0_0_3px_var(--accent-soft)]",
    isDragging && "border-accent-ring shadow-lift",
    !page.removed && !isSelected && !isDragging && "border-line/70",
  );

  const content = (
    <>
      <motion.img
        src={page.thumbnail}
        alt=""
        draggable={false}
        animate={{ rotate: page.angle, scale }}
        transition={springs.snappy}
        className="pointer-events-none max-h-[92%] max-w-[92%] object-contain shadow-[0_1px_3px_rgb(var(--shadow-rgb)/0.2)] select-none"
      />
      <span className="absolute top-1.5 left-1.5 rounded-md bg-ink/75 px-1.5 py-0.5 text-[0.75rem] font-semibold text-surface tabular-nums">
        {position}
      </span>
      {isSelected && (
        <span className="absolute top-1.5 right-1.5 flex size-6 items-center justify-center rounded-full bg-accent text-on-accent">
          <Check className="size-3.5" aria-hidden />
        </span>
      )}
      {rotation !== 0 && !page.removed && (
        <span className="absolute right-1.5 bottom-1.5 rounded-md bg-surface/90 px-1.5 py-0.5 text-[0.75rem] font-semibold text-ink-soft tabular-nums">
          {rotation}°
        </span>
      )}
      {page.removed && (
        <span className="absolute inset-0 flex flex-col items-center justify-center gap-1 bg-danger-soft/85 text-danger">
          <Trash2 className="size-6" aria-hidden />
          <span className="text-[0.8125rem] font-semibold">Se eliminará</span>
        </span>
      )}
    </>
  );

  if (mode === "organize") {
    return (
      <div className="flex flex-col gap-1">
        <div
          ref={dragHandle?.ref}
          {...dragHandle?.attributes}
          {...dragHandle?.listeners}
          aria-label={`Página ${page.index + 1}. Arrastra para moverla`}
          className={cx(frame, "cursor-grab touch-manipulation active:cursor-grabbing")}
        >
          {content}
        </div>
        <div className="flex items-center justify-center gap-0.5">
          <IconButton label={`Girar ${pageName} a la izquierda`} disabled={disabled || page.removed} onClick={() => onRotate(page.id, -90)}>
            <RotateCcw className="size-4" aria-hidden />
          </IconButton>
          <IconButton label={`Girar ${pageName} a la derecha`} disabled={disabled || page.removed} onClick={() => onRotate(page.id, 90)}>
            <RotateCw className="size-4" aria-hidden />
          </IconButton>
          <IconButton
            label={page.removed ? `Recuperar ${pageName}` : `Quitar ${pageName}`}
            disabled={disabled}
            onClick={() => onToggleRemoved(page.id)}
            className={page.removed ? "text-danger" : "hover:bg-danger-soft hover:text-danger"}
          >
            {page.removed ? <Undo2 className="size-4" aria-hidden /> : <Trash2 className="size-4" aria-hidden />}
          </IconButton>
        </div>
      </div>
    );
  }

  const pressed = mode === "delete" ? page.removed : mode === "extract" ? page.selected : undefined;

  return (
    <motion.button
      type="button"
      disabled={disabled}
      whileTap={{ scale: 0.97 }}
      transition={springs.snappy}
      onClick={() => onActivate(page.id)}
      aria-pressed={pressed}
      aria-label={ACTIVATE_LABEL[mode](pageName)}
      className={cx(frame, "cursor-pointer hover:border-subtle disabled:cursor-not-allowed")}
    >
      {content}
      {mode === "rotate" && (
        <span className="absolute inset-x-0 bottom-1.5 flex justify-center opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-visible:opacity-100">
          <span className="flex size-8 items-center justify-center rounded-full bg-ink/75 text-surface">
            <RotateCw className="size-4" aria-hidden />
          </span>
        </span>
      )}
    </motion.button>
  );
}
