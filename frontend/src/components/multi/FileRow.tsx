import { ChevronDown, ChevronUp, FileText, GripVertical, X } from "lucide-react";
import { Reorder, useDragControls } from "motion/react";
import { useState } from "react";

import type { QueuedFile } from "../../hooks/useFileQueue";
import { useObjectUrl } from "../../hooks/useObjectUrl";
import { cx } from "../../lib/cx";
import { formatBytes } from "../../lib/files";
import { exitTransition, springs } from "../../lib/motion";
import { IconButton } from "../ui/IconButton";

interface FileRowProps {
  item: QueuedFile;
  position: number;
  total: number;
  disabled: boolean;
  onMove: (id: string, offset: -1 | 1) => void;
  onRemove: (id: string) => void;
}

export function FileRow({ item, position, total, disabled, onMove, onRemove }: FileRowProps) {
  const dragControls = useDragControls();
  // La sombra se aplica por clase (con tokens de tema): Motion no puede interpolar variables CSS.
  const [isDragging, setIsDragging] = useState(false);
  const { id, file } = item;
  const previewUrl = useObjectUrl(file.type.startsWith("image/") ? file : null);

  return (
    <Reorder.Item
      as="li"
      value={item}
      // El arrastre solo empieza desde el asa: los botones de la fila siguen siendo clicables.
      dragListener={false}
      dragControls={dragControls}
      onDragStart={() => setIsDragging(true)}
      onDragEnd={() => setIsDragging(false)}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97, transition: exitTransition }}
      whileDrag={{ scale: 1.015 }}
      transition={springs.snappy}
      className={cx(
        "relative flex items-center gap-1.5 rounded-control border border-line/70 bg-surface py-2 pr-2 pl-1 transition-shadow duration-200",
        isDragging && "z-10 shadow-lift",
      )}
    >
      <span
        aria-hidden
        onPointerDown={(event) => {
          if (!disabled) dragControls.start(event);
        }}
        className="flex h-10 w-8 cursor-grab touch-none items-center justify-center text-muted active:cursor-grabbing"
      >
        <GripVertical className="size-4" />
      </span>

      <span className="w-5 text-center text-[0.8125rem] font-semibold text-muted tabular-nums">{position}</span>

      {/* Decorativo: en pantallas estrechas cede su espacio al nombre del archivo. */}
      {previewUrl ? (
        <img
          src={previewUrl}
          alt=""
          className="ml-1 hidden size-9 shrink-0 rounded-[0.625rem] border border-line/60 object-cover sm:block"
        />
      ) : (
        <span className="ml-1 hidden size-9 items-center justify-center rounded-[0.625rem] bg-accent-soft text-accent sm:flex">
          <FileText className="size-[1.125rem]" aria-hidden />
        </span>
      )}

      <div className="min-w-0 flex-1 px-2">
        {/* Envolver antes que recortar: en móvil un nombre cortado no se puede leer de otra forma. */}
        <p
          className="line-clamp-2 text-[0.9375rem] leading-snug font-medium tracking-[-0.01em] [overflow-wrap:anywhere] text-ink"
          title={file.name}
        >
          {file.name}
        </p>
        <p className="text-[0.8125rem] text-muted tabular-nums">{formatBytes(file.size)}</p>
      </div>

      <div className="flex items-center gap-0.5">
        <IconButton label={`Subir ${file.name}`} disabled={disabled || position === 1} onClick={() => onMove(id, -1)}>
          <ChevronUp className="size-[1.125rem]" aria-hidden />
        </IconButton>
        <IconButton label={`Bajar ${file.name}`} disabled={disabled || position === total} onClick={() => onMove(id, 1)}>
          <ChevronDown className="size-[1.125rem]" aria-hidden />
        </IconButton>
        <IconButton
          label={`Quitar ${file.name}`}
          disabled={disabled}
          onClick={() => onRemove(id)}
          className="hover:bg-danger-soft hover:text-danger"
        >
          <X className="size-[1.125rem]" aria-hidden />
        </IconButton>
      </div>
    </Reorder.Item>
  );
}
