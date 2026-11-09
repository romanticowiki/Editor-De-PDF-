import { DEFAULT_API_BASE_URL } from "./defaults";

export const env = {
  apiBaseUrl: (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/+$/, ""),
} as const;
