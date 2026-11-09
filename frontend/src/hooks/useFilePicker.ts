import { type ChangeEvent, type ComponentPropsWithRef, useCallback, useRef } from "react";

import { type FileAccept, acceptAttribute } from "../lib/files";

interface UseFilePickerOptions {
  accept: FileAccept;
  multiple: boolean;
  onFiles: (files: File[]) => void;
}

/** Selector de archivos nativo, invisible, que se abre desde cualquier botón. */
export function useFilePicker({ accept, multiple, onFiles }: UseFilePickerOptions) {
  const inputRef = useRef<HTMLInputElement>(null);
  const open = useCallback(() => inputRef.current?.click(), []);

  const inputProps: ComponentPropsWithRef<"input"> = {
    ref: inputRef,
    type: "file",
    accept: acceptAttribute(accept),
    multiple,
    hidden: true,
    tabIndex: -1,
    onChange: (event: ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(event.target.files ?? []);
      // Vaciar el input permite volver a elegir el mismo archivo.
      event.target.value = "";
      if (files.length > 0) onFiles(files);
    },
  };

  return { open, inputProps };
}
