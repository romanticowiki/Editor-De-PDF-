import { FileText, RefreshCw, X } from "lucide-react";
import { motion } from "motion/react";

import { useFileDrop } from "../../hooks/useFileDrop";
import { useFilePicker } from "../../hooks/useFilePicker";
import { cx } from "../../lib/cx";
import { type FileAccept, formatBytes } from "../../lib/files";
import { springs } from "../../lib/motion";
import { Button } from "../ui/Button";

interface SelectedFileProps {
  file: File;
  accept: FileAccept;
  disabled: boolean;
  onFiles: (files: File[]) => void;
  onRemove: () => void;
}

/** Archivo elegido. Soltar otro encima (o «Cambiar archivo») lo reemplaza. */
export function SelectedFile({ file, accept, disabled, onFiles, onRemove }: SelectedFileProps) {
  const { isDragging, dropHandlers } = useFileDrop({ disabled, onFiles });
  const picker = useFilePicker({ accept, multiple: false, onFiles });
  const isActive = isDragging && !disabled;

  return (
    <div
      {...dropHandlers}
      className={cx(
        "flex min-h-72 flex-1 flex-col items-center justify-center gap-5 overflow-y-auto rounded-panel border-[1.5px] px-6 py-8 text-center transition-[background-color,border-color] duration-200 ease-out-quart lg:min-h-0",
        isActive ? "border-dashed border-accent-ring bg-accent-soft/70" : "border-transparent bg-surface-sunken/80",
      )}
    >
      <motion.span
        key={`${file.name}:${file.size}:${file.lastModified}`}
        initial={{ opacity: 0, scale: 0.9, y: 6 }}
        animate={{ opacity: 1, scale: isActive ? 1.06 : 1, y: 0 }}
        transition={springs.playful}
        className="flex size-20 shrink-0 items-center justify-center rounded-[1.375rem] bg-surface text-accent shadow-lift"
      >
        <FileText className="size-9" aria-hidden />
      </motion.span>

      <div className="flex max-w-md flex-col gap-1">
        <p className="line-clamp-2 text-lg font-semibold tracking-[-0.015em] [overflow-wrap:anywhere] text-ink" title={file.name}>
          {file.name}
        </p>
        <p className="text-sm text-muted tabular-nums">{formatBytes(file.size)}</p>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-2">
        <Button variant="quiet" icon={<RefreshCw className="size-4" aria-hidden />} onClick={picker.open} disabled={disabled}>
          Cambiar archivo
        </Button>
        <Button variant="quiet" icon={<X className="size-4" aria-hidden />} onClick={onRemove} disabled={disabled}>
          Quitar
        </Button>
      </div>

      <p aria-live="polite" className="text-[0.8125rem] text-muted">
        {isActive ? "Suéltalo para reemplazarlo" : "También puedes soltar otro archivo aquí"}
      </p>
      <input {...picker.inputProps} />
    </div>
  );
}
