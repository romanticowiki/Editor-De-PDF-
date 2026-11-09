import { useEffect, useState } from "react";

import { ApiError } from "../services/apiClient";
import { fetchHealth } from "../services/healthService";

export type ApiHealth = "checking" | "online" | "offline";

// Apagado se reintenta antes: la persona suele estar arrancando el motor en ese momento.
const ONLINE_POLL_MS = 20_000;
const OFFLINE_POLL_MS = 4_000;

export function useApiHealth(): ApiHealth {
  const [health, setHealth] = useState<ApiHealth>("checking");

  useEffect(() => {
    let disposed = false;
    let timer: number | undefined;
    let controller: AbortController | undefined;

    const check = async () => {
      controller = new AbortController();
      let next: ApiHealth;
      try {
        await fetchHealth(controller.signal);
        next = "online";
      } catch (error) {
        // Un 429 demuestra que el motor responde.
        next = error instanceof ApiError && error.kind === "rate_limited" ? "online" : "offline";
      }
      if (disposed) return;
      setHealth(next);
      timer = window.setTimeout(check, next === "online" ? ONLINE_POLL_MS : OFFLINE_POLL_MS);
    };

    void check();
    return () => {
      disposed = true;
      controller?.abort();
      window.clearTimeout(timer);
    };
  }, []);

  return health;
}
