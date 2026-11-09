import { type DOMAttributes, type DragEvent, useRef, useState } from "react";

interface UseFileDropOptions {
  disabled: boolean;
  onFiles: (files: File[]) => void;
}

type DropHandlers = Pick<DOMAttributes<HTMLElement>, "onDragEnter" | "onDragOver" | "onDragLeave" | "onDrop">;

function carriesFiles(event: DragEvent<HTMLElement>): boolean {
  return Array.from(event.dataTransfer.types).includes("Files");
}

export function useFileDrop({ disabled, onFiles }: UseFileDropOptions): { isDragging: boolean; dropHandlers: DropHandlers } {
  const [isDragging, setIsDragging] = useState(false);
  // dragenter/dragleave también se disparan al cruzar hijos: contamos la profundidad
  // para que el estado no parpadee.
  const depth = useRef(0);

  const dropHandlers: DropHandlers = {
    onDragEnter: (event) => {
      if (!carriesFiles(event)) return;
      event.preventDefault();
      depth.current += 1;
      setIsDragging(true);
    },
    onDragOver: (event) => {
      if (!carriesFiles(event)) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = disabled ? "none" : "copy";
    },
    onDragLeave: (event) => {
      if (!carriesFiles(event)) return;
      depth.current = Math.max(0, depth.current - 1);
      if (depth.current === 0) setIsDragging(false);
    },
    onDrop: (event) => {
      if (!carriesFiles(event)) return;
      event.preventDefault();
      depth.current = 0;
      setIsDragging(false);
      if (disabled) return;
      const files = Array.from(event.dataTransfer.files);
      if (files.length > 0) onFiles(files);
    },
  };

  return { isDragging, dropHandlers };
}
