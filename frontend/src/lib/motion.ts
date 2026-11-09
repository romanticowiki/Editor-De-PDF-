import type { Transition } from "motion/react";

// Tokens de movimiento: un solo ritmo para toda la app. Espejo en tailwind.config.js.
export const EASE_IN_QUART = [0.5, 0, 0.75, 0] as const;

export const springs = {
  // Críticamente amortiguado: sin rebote, para casi todo.
  snappy: { type: "spring", bounce: 0, duration: 0.3 },
  gentle: { type: "spring", bounce: 0, duration: 0.5 },
  // Rebote solo donde hubo un gesto físico (arrastrar y soltar).
  playful: { type: "spring", bounce: 0.25, duration: 0.45 },
} as const satisfies Record<string, Transition>;

// Las salidas son más rápidas que las entradas.
export const exitTransition = { duration: 0.18, ease: EASE_IN_QUART } as const satisfies Transition;
