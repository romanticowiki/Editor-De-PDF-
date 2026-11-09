import type { Rgb } from "../components/editor/types";

export function hexToRgb(hex: string): Rgb {
  if (!/^#[\da-f]{6}$/i.test(hex)) throw new Error("Color hexadecimal no válido.");
  const value = Number.parseInt(hex.slice(1), 16);
  return [(value >> 16) / 255, ((value >> 8) & 255) / 255, (value & 255) / 255];
}

export function rgbToHex(color: Rgb): string {
  return `#${color.map((channel) => Math.round(channel * 255).toString(16).padStart(2, "0")).join("")}`;
}
