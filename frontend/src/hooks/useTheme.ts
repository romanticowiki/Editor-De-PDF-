import { useCallback, useEffect, useState } from "react";

export type ResolvedTheme = "light" | "dark";
type ThemePreference = ResolvedTheme | "system";

const STORAGE_KEY = "pdf-local:theme";
const DARK_QUERY = "(prefers-color-scheme: dark)";

export function readThemePreference(): ThemePreference {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored === "light" || stored === "dark" ? stored : "system";
  } catch {
    return "system"; // almacenamiento bloqueado (modo privado): seguimos al sistema
  }
}

function resolveTheme(preference: ThemePreference): ResolvedTheme {
  if (preference !== "system") return preference;
  return window.matchMedia(DARK_QUERY).matches ? "dark" : "light";
}

export function applyTheme(preference: ThemePreference): ResolvedTheme {
  const resolved = resolveTheme(preference);
  document.documentElement.dataset.theme = resolved;
  return resolved;
}

export function useTheme(): { theme: ResolvedTheme; toggle: () => void } {
  const [preference, setPreference] = useState<ThemePreference>(readThemePreference);
  const [theme, setTheme] = useState<ResolvedTheme>(() => resolveTheme(preference));

  useEffect(() => {
    setTheme(applyTheme(preference));
    if (preference !== "system") return;

    // Sin elección explícita, el tema acompaña al del sistema en vivo.
    const query = window.matchMedia(DARK_QUERY);
    const handleChange = () => setTheme(applyTheme("system"));
    query.addEventListener("change", handleChange);
    return () => query.removeEventListener("change", handleChange);
  }, [preference]);

  const toggle = useCallback(() => {
    const next: ResolvedTheme = theme === "dark" ? "light" : "dark";
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Sin almacenamiento el cambio dura hasta recargar: aceptable.
    }
    setPreference(next);
  }, [theme]);

  return { theme, toggle };
}
