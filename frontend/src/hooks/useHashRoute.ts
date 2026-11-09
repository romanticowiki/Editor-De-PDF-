import { useSyncExternalStore } from "react";

function subscribe(onChange: () => void): () => void {
  window.addEventListener("hashchange", onChange);
  return () => window.removeEventListener("hashchange", onChange);
}

function readPath(): string {
  const path = window.location.hash.replace(/^#/, "");
  return path.startsWith("/") ? path : "/";
}

/** Rutas con hash (#/comprimir-pdf): enlaces directos y botón «atrás» sin servidor de rutas. */
export function useHashRoute(): string {
  return useSyncExternalStore(subscribe, readPath, () => "/");
}
