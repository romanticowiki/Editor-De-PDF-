import { useCallback, useState } from "react";

import { MAX_UPLOAD_BYTES } from "../config/limits";
import { type FileAccept, type FileRejection, partitionFiles } from "../lib/files";

/** Un único archivo: elegir otro lo reemplaza (en vez de rechazarlo por límite). */
export function useSelectedFile(accept: FileAccept) {
  const [file, setFile] = useState<File | null>(null);

  const select = useCallback(
    (incoming: readonly File[]): FileRejection[] => {
      const { accepted, rejected } = partitionFiles([], incoming, { accept, maxFiles: 1, maxFileBytes: MAX_UPLOAD_BYTES });
      const [first] = accepted;
      if (first) setFile(first);
      return rejected;
    },
    [accept],
  );

  const clear = useCallback(() => setFile(null), []);

  return { file, select, clear };
}
