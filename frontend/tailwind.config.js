/**
 * Sistema de diseño retro-cálido, claro y oscuro.
 * Los valores viven como variables CSS en src/index.css; aquí solo se exponen con nombres
 * semánticos. Los componentes nunca usan hex: cambiar el tema = tocar index.css.
 */

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "var(--canvas)",
        surface: { DEFAULT: "var(--surface)", sunken: "var(--surface-sunken)" },
        line: "var(--line)",
        ink: { DEFAULT: "var(--ink)", soft: "var(--ink-soft)" },
        muted: "var(--muted)",
        subtle: "var(--subtle)",
        accent: {
          DEFAULT: "var(--accent)",
          hover: "var(--accent-hover)",
          ring: "var(--accent-ring)",
          soft: "var(--accent-soft)",
        },
        "on-accent": "var(--on-accent)",
        success: { DEFAULT: "var(--success)", soft: "var(--success-soft)" },
        warning: { DEFAULT: "var(--warning)", soft: "var(--warning-soft)" },
        danger: { DEFAULT: "var(--danger)", soft: "var(--danger-soft)" },
        teal: { DEFAULT: "var(--teal)", soft: "var(--teal-soft)" },
      },
      fontFamily: {
        sans: ['"Manrope Variable"', "ui-sans-serif", "system-ui", "sans-serif"],
      },
      // Radios concéntricos: radio interior = radio exterior − padding (28 − 8 = 20).
      borderRadius: {
        card: "1.75rem",
        panel: "1.25rem",
        control: "0.875rem",
      },
      transitionTimingFunction: {
        "out-quart": "cubic-bezier(0.25, 1, 0.5, 1)",
        "in-quart": "cubic-bezier(0.5, 0, 0.75, 0)",
      },
      boxShadow: {
        lift: "inset 0 1px 0 var(--glass-highlight), 0 1px 2px rgb(var(--shadow-rgb) / 0.08), 0 10px 24px -14px rgb(var(--shadow-rgb) / 0.4)",
      },
    },
  },
};
