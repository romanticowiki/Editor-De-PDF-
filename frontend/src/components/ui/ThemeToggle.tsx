import { Moon, Sun } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";

import { useTheme } from "../../hooks/useTheme";
import { exitTransition, springs } from "../../lib/motion";
import { IconButton } from "./IconButton";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const isDark = theme === "dark";

  return (
    <IconButton
      label={isDark ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
      round
      onClick={toggle}
      className="glass [--glass-alpha:0.5]"
    >
      <AnimatePresence mode="popLayout" initial={false}>
        <motion.span
          key={theme}
          initial={{ opacity: 0, rotate: -60, scale: 0.6 }}
          animate={{ opacity: 1, rotate: 0, scale: 1 }}
          exit={{ opacity: 0, rotate: 60, scale: 0.6, transition: exitTransition }}
          transition={springs.snappy}
          className="flex"
        >
          {isDark ? <Moon className="size-4" aria-hidden /> : <Sun className="size-4" aria-hidden />}
        </motion.span>
      </AnimatePresence>
    </IconButton>
  );
}
