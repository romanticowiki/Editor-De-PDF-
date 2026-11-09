import { useEffect } from "react";

/** Si sueltas un PDF fuera de la zona, el navegador lo abriría y perderías tu lista. */
export function usePreventWindowFileDrop(): void {
  useEffect(() => {
    const prevent = (event: DragEvent) => {
      if (event.dataTransfer?.types.includes("Files")) event.preventDefault();
    };
    window.addEventListener("dragover", prevent);
    window.addEventListener("drop", prevent);
    return () => {
      window.removeEventListener("dragover", prevent);
      window.removeEventListener("drop", prevent);
    };
  }, []);
}
