import { FileText, RefreshCw, X } from "lucide-react";

import { useFilePicker } from "../../hooks/useFilePicker";
import { type FileAccept, formatBytes } from "../../lib/files";
import { IconButton } from "../ui/IconButton";

interface LoadedFileHeaderProps {
  file: File;
  detail: string;
  accept: FileAccept;
  disabled: boolean;
  onFiles: (files: File[]) => void;
  onRemove: () => void;
}

/** Cabecera compacta del archivo abierto en los editores (páginas, formularios). */
export function LoadedFileHeader({ file, detail, accept, disabled, onFiles, onRemove }: LoadedFileHeaderProps) {
  const picker = useFilePicker({ accept, multiple: false, onFiles });

  return (
    <div className="flex shrink-0 items-center gap-3 px-2 pt-1 pb-3">
      <span className="flex size-10 shrink-0 items-center justify-center rounded-[0.75rem] bg-accent-soft text-accent">
        <FileText className="size-5" aria-hidden />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[0.9375rem] font-semibold tracking-[-0.01em] text-ink" title={file.name}>
          {file.name}
        </p>
        <p className="text-[0.8125rem] text-muted tabular-nums">
          {formatBytes(file.size)} · {detail}
        </p>
      </div>
      <IconButton label="Cambiar archivo" onClick={picker.open} disabled={disabled}>
        <RefreshCw className="size-4" aria-hidden />
      </IconButton>
      <IconButton label="Quitar archivo" onClick={onRemove} disabled={disabled}>
        <X className="size-[1.125rem]" aria-hidden />
      </IconButton>
      <input {...picker.inputProps} />
    </div>
  );
}
