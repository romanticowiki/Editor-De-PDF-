import type { NPoint } from "../components/editor/types";

export function appendStrokePoint(points: NPoint[], point: NPoint, width: number, height: number): NPoint[] {
  const last = points[points.length - 1]!;
  if (points.length >= 2999 || Math.hypot((point[0] - last[0]) * width, (point[1] - last[1]) * height) < 0.35) return points;
  return [...points, point];
}

export function finishStroke(points: readonly NPoint[], point: NPoint): NPoint[] {
  const last = points[points.length - 1]!;
  const result = point[0] === last[0] && point[1] === last[1] ? [...points] : [...points.slice(0, 2999), point];
  return result.length > 1 ? result : [];
}

export function editorNumber(value: string, min: number, max: number, step: number): number | null {
  const number = Number(value);
  return value.trim() && Number.isFinite(number) && number >= min && number <= max && Number.isInteger(number / step) ? number : null;
}
