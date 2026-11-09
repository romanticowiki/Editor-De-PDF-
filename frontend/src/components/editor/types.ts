/** Herramientas del editor visual. */
export type EditorTool = "text" | "highlight" | "draw" | "patch" | "signature";

export type Rgb = readonly [number, number, number];

/** Rectángulo en coordenadas NORMALIZADAS (0..1 respecto a la página): no dependen del zoom. */
export interface NRect {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

export type NPoint = readonly [number, number];

interface Base {
  id: string;
  page: number; // índice de página, desde 0
}

export interface TextAnno extends Base {
  kind: "text";
  nx: number;
  ny: number;
  text: string;
  size: number; // puntos PDF
  color: Rgb;
}

export interface TextBoxAnno extends Base {
  kind: "textbox";
  rect: NRect;
  text: string;
  size: number;
  color: Rgb;
}

export interface FieldAnno extends Base {
  kind: "field";
  name: string;
  value: string | boolean;
  size: number;
}

export type TextEntry = HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement;

export interface HighlightAnno extends Base {
  kind: "highlight";
  rect: NRect;
  color: Rgb;
}

export interface PatchAnno extends Base {
  kind: "patch";
  rect: NRect;
  text: string;
  size: number;
  color: Rgb;
  fill: Rgb;
}

export interface DrawAnno extends Base {
  kind: "draw";
  strokes: NPoint[][];
  color: Rgb;
  width: number; // puntos PDF
}

export interface ImageAnno extends Base {
  kind: "image";
  rect: NRect;
  imageIndex: number;
  previewUrl: string;
}

export type Annotation = TextAnno | TextBoxAnno | FieldAnno | HighlightAnno | PatchAnno | DrawAnno | ImageAnno;

export interface SignatureAsset {
  index: number;
  previewUrl: string;
  aspect: number; // ancho / alto
}
