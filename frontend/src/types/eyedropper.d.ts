export {};

declare global {
  interface EyeDropperResult {
    sRGBHex: string;
  }

  interface EyeDropper {
    open(options?: { signal?: AbortSignal }): Promise<EyeDropperResult>;
  }

  interface Window {
    EyeDropper?: { new (): EyeDropper };
  }
}
