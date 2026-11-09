import { useCallback, useState } from "react";

import { moveItem } from "../lib/array";
import { type FileLimits, type FileRejection, partitionFiles } from "../lib/files";

export interface QueuedFile {
  readonly id: string;
  readonly file: File;
}

function toQueuedFile(file: File): QueuedFile {
  return { id: crypto.randomUUID(), file };
}

/** Lista ordenada de archivos. `limits` debe ser una referencia estable (constante de módulo). */
export function useFileQueue(limits: FileLimits) {
  const [items, setItems] = useState<QueuedFile[]>([]);

  const addFiles = useCallback(
    (incoming: readonly File[]): FileRejection[] => {
      const { accepted, rejected } = partitionFiles(
        items.map(({ file }) => file),
        incoming,
        limits,
      );
      if (accepted.length > 0) setItems((current) => [...current, ...accepted.map(toQueuedFile)]);
      return rejected;
    },
    [items, limits],
  );

  const removeFile = useCallback((id: string) => {
    setItems((current) => current.filter((item) => item.id !== id));
  }, []);

  const moveFile = useCallback((id: string, offset: number) => {
    setItems((current) => {
      const from = current.findIndex((item) => item.id === id);
      return moveItem(current, from, from + offset);
    });
  }, []);

  const clear = useCallback(() => setItems([]), []);

  return { items, addFiles, removeFile, moveFile, reorder: setItems, clear };
}
