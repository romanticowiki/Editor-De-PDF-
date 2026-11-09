import { AnimatePresence, Reorder } from "motion/react";

import type { QueuedFile } from "../../hooks/useFileQueue";
import { FileRow } from "./FileRow";

interface FileListProps {
  items: QueuedFile[];
  disabled: boolean;
  onReorder: (items: QueuedFile[]) => void;
  onMove: (id: string, offset: -1 | 1) => void;
  onRemove: (id: string) => void;
}

export function FileList({ items, disabled, onReorder, onMove, onRemove }: FileListProps) {
  return (
    <Reorder.Group
      as="ol"
      axis="y"
      values={items}
      onReorder={onReorder}
      aria-label="Orden de los archivos"
      className="relative flex flex-col gap-1.5"
    >
      <AnimatePresence initial={false} mode="popLayout">
        {items.map((item, index) => (
          <FileRow
            key={item.id}
            item={item}
            position={index + 1}
            total={items.length}
            disabled={disabled}
            onMove={onMove}
            onRemove={onRemove}
          />
        ))}
      </AnimatePresence>
    </Reorder.Group>
  );
}
