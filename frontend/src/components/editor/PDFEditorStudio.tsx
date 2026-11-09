import { ChevronLeft, ChevronRight, Loader2, Minus, Plus, X } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { FAILURE_TITLE, apiErrorToast, rejectionToast, successToast, uploadHint } from "../../copy/messages";
import type { ApiHealth } from "../../hooks/useApiHealth";
import { useSelectedFile } from "../../hooks/useSelectedFile";
import { useToolJob } from "../../hooks/useToolJob";
import { buildOperations } from "../../lib/editorPayload";
import { imageRect } from "../../lib/editorGeometry";
import { newId } from "../../lib/id";
import { ApiError } from "../../services/apiClient";
import { type EditorPage, fetchEditorPages, processEditor } from "../../services/editorService";
import { PDF_ACCEPT } from "../../tools/accept";
import type { EditorToolDefinition } from "../../tools/types";
import { Dropzone } from "../dropzone/Dropzone";
import { ToolWorkspace } from "../tool/ToolWorkspace";
import { useToast } from "../toast/toastContext";
import { EditorStage } from "./EditorStage";
import { EditorToolbar } from "./EditorToolbar";
import type { Annotation, EditorTool, NRect, Rgb, SignatureAsset, TextEntry } from "./types";

interface PDFEditorStudioProps {
  tool: EditorToolDefinition;
  apiHealth: ApiHealth;
}

export function PDFEditorStudio({ tool, apiHealth }: PDFEditorStudioProps) {
  const { notify } = useToast();
  const { file, select, clear } = useSelectedFile(tool.accept);
  const { isRunning, run } = useToolJob();

  const [pages, setPages] = useState<EditorPage[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [pageIndex, setPageIndex] = useState(0);

  const [activeTool, setActiveTool] = useState<EditorTool>("text");
  const [color, setColor] = useState<Rgb>([0.63, 0.32, 0.18]);
  const [fill, setFill] = useState<Rgb>([1, 1, 1]);
  const [size, setSize] = useState(16);
  const [strokeWidth, setStrokeWidth] = useState(2);
  const [selectedTextId, setSelectedTextId] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const textInputRef = useRef<TextEntry>(null);

  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [signatures, setSignatures] = useState<SignatureAsset[]>([]);
  const imageFiles = useRef<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [activeSignature, setActiveSignature] = useState<number | null>(null);
  const [dirty, setDirty] = useState(false);

  const urlsRef = useRef<string[]>([]);

  // Cargar (rasterizar) las páginas cada vez que se elige un archivo nuevo.
  useEffect(() => {
    if (!file) return;
    setPages(null);
    setLoadError(null);
    setAnnotations([]);
    setSelectedTextId(null);
    setSignatures([]);
    imageFiles.current = [];
    setActiveSignature(null);
    setPageIndex(0);
    setDirty(false);
    setZoom(1);

    const controller = new AbortController();
    fetchEditorPages(file, controller.signal)
      .then((next) => {
        if (!controller.signal.aborted) setPages(next);
      })
      .catch((error) => {
        if (!controller.signal.aborted) setLoadError(error instanceof ApiError ? error.message : "No pudimos abrir el PDF.");
      });
    return () => controller.abort();
  }, [file]);

  // Aviso al salir con trabajo sin guardar.
  useEffect(() => {
    if (!dirty) return;
    const handler = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  useEffect(() => () => {
    urlsRef.current.forEach((url) => URL.revokeObjectURL(url));
    urlsRef.current = [];
  }, []);

  const addAnnotation = useCallback((annotation: Annotation) => {
    setAnnotations((prev) => [...prev, annotation]);
    setDirty(true);
  }, []);

  const setText = useCallback((id: string, text: string) => {
    setAnnotations((prev) => prev.map((a) => a.id !== id ? a : a.kind === "field" ? { ...a, value: text } : a.kind === "text" || a.kind === "patch" || a.kind === "textbox" ? { ...a, text } : a));
    setDirty(true);
  }, []);

  const selectText = useCallback((id: string | null, fontSize: number) => {
    setSelectedTextId(id);
    setSize(fontSize);
  }, []);

  const updateSize = useCallback((next: number) => {
    setSize(next);
    setAnnotations((prev) => prev.map((a) => a.id === selectedTextId && (a.kind === "text" || a.kind === "textbox" || a.kind === "patch" || (a.kind === "field" && typeof a.value === "string")) ? { ...a, size: next } : a));
    if (selectedTextId) setDirty(true);
  }, [selectedTextId]);

  const updateColor = useCallback((next: Rgb) => {
    setColor(next);
    setAnnotations((prev) => prev.map((a) => a.id === selectedTextId && (a.kind === "text" || a.kind === "textbox" || a.kind === "patch") ? { ...a, color: next } : a));
    if (selectedTextId) setDirty(true);
  }, [selectedTextId]);

  const deleteAnnotation = useCallback((id: string) => {
    setAnnotations((prev) => prev.filter((a) => a.id !== id));
    setDirty(true);
  }, []);

  const updateAnnotationRect = useCallback((id: string, rect: NRect) => {
    setAnnotations((prev) => prev.map((a) => a.id === id && a.kind === "image" ? { ...a, rect } : a));
    setDirty(true);
  }, []);

  const undo = useCallback(() => {
    setAnnotations((prev) => prev.slice(0, -1));
    setDirty(true);
  }, []);

  const uploadSignature = useCallback((image: File) => {
    const current = pages?.[pageIndex];
    if (!current) return;
    if (!(image.type === "image/png" || image.type === "image/jpeg" || (!image.type && /\.(png|jpe?g)$/i.test(image.name)))) {
      notify({ tone: "error", title: "Formato no compatible", description: "Elige una imagen PNG o JPG." });
      return;
    }
    if (image.size === 0 || image.size > 5 * 1024 * 1024 || imageFiles.current.length >= 20) {
      notify({ tone: "error", title: "No pudimos añadir la imagen", description: "Usa imágenes de hasta 5 MB. Puedes subir hasta 20 por documento." });
      return;
    }
    setIsUploading(true);
    const url = URL.createObjectURL(image);
    urlsRef.current.push(url);
    const probe = new Image();
    const rejectImage = () => {
      if (!urlsRef.current.includes(url)) return;
      URL.revokeObjectURL(url);
      urlsRef.current = urlsRef.current.filter((item) => item !== url);
      setIsUploading(false);
      notify({ tone: "error", title: "No pudimos abrir la imagen", description: "Usa un PNG o JPG válido, con lados de hasta 6000 píxeles." });
    };
    probe.onload = () => {
      if (!urlsRef.current.includes(url)) return;
      if (probe.naturalWidth > 6000 || probe.naturalHeight > 6000) {
        rejectImage();
        return;
      }
      const aspect = probe.naturalWidth / Math.max(1, probe.naturalHeight);
      const index = imageFiles.current.length;
      imageFiles.current.push(image);
      setSignatures((prev) => [...prev, { index, previewUrl: url, aspect }]);
      setActiveSignature(index);
      setActiveTool("signature");
      addAnnotation({ id: newId(), kind: "image", page: pageIndex, rect: imageRect(0.5, 0.5, aspect, current.width, current.height), imageIndex: index, previewUrl: url });
      setIsUploading(false);
    };
    probe.onerror = rejectImage;
    probe.src = url;
  }, [pages, pageIndex, addAnnotation, notify]);

  const clearFile = useCallback(() => {
    urlsRef.current.forEach((url) => URL.revokeObjectURL(url));
    urlsRef.current = [];
    imageFiles.current = [];
    setIsUploading(false);
    clear();
    setPages(null);
    setDirty(false);
  }, [clear]);

  const handleSave = useCallback(async () => {
    if (!file || !pages) return;
    const input = textInputRef.current;
    // Confirmar el valor visible sin depender del siguiente render tras blur.
    const confirmed = input ? annotations.map((a) => a.id !== input.dataset.annotationId ? a : a.kind === "field" ? { ...a, value: input.value } : a.kind === "text" || a.kind === "patch" || a.kind === "textbox" ? { ...a, text: input.value } : a) : annotations;
    input?.blur();
    const built = buildOperations(confirmed, pages);
    if (built.operations.length === 0) {
      notify({ tone: "info", title: "Nada que guardar", description: "Añade alguna anotación antes de guardar." });
      return;
    }
    const outcome = await run((signal) => processEditor(file, JSON.stringify(built), imageFiles.current, signal));
    if (outcome.ok) {
      setDirty(false);
      notify(successToast(outcome.download));
    } else {
      notify(apiErrorToast(outcome.error, FAILURE_TITLE));
    }
  }, [file, pages, annotations, run, notify]);

  const activeAsset = useMemo(
    () => signatures.find((asset) => asset.index === activeSignature) ?? null,
    [signatures, activeSignature],
  );
  const pageAnnotations = useMemo(() => annotations.filter((a) => a.page === pageIndex), [annotations, pageIndex]);

  if (!file || !pages) {
    return (
      <div className="glass flex min-h-0 flex-1 flex-col items-center justify-center rounded-card p-6">
        {file && !loadError ? (
          <div className="flex flex-col items-center gap-3 text-muted">
            <Loader2 className="size-6 animate-spin text-accent" />
            <p className="text-[0.9375rem]">Preparando las páginas…</p>
          </div>
        ) : (
          <div className="w-full max-w-xl">
            {loadError && <p className="mb-4 text-center text-[0.9375rem] text-danger">{loadError}</p>}
            <Dropzone
              accept={tool.accept}
              hint={apiHealth === "offline" ? "Enciende el motor local para empezar." : uploadHint(PDF_ACCEPT, 1)}
              disabled={apiHealth === "offline"}
              onFiles={(incoming) => {
                const rejected = select(incoming);
                if (rejected.length > 0) notify(rejectionToast(rejected, { acceptLabel: tool.accept.label, maxFiles: 1 }));
              }}
            />
          </div>
        )}
      </div>
    );
  }

  const current = pages[pageIndex]!;
  const selectedText = annotations.find((a) => a.id === selectedTextId);

  return (
    <ToolWorkspace
      asideLabel="Herramientas del editor"
      main={
        <div className="flex min-h-0 flex-1 flex-col">
          {current.hasFormFields && <div className="mb-2 rounded-control border border-line bg-surface p-3 text-sm text-ink-soft">
            Este PDF contiene campos editables. Toca un campo para escribir o una casilla para marcarla. Se conservarán editables.
            <a href="#/rellenar-formulario" onClick={(event) => { if (dirty) { event.preventDefault(); notify({ tone: "info", title: "Guarda tus cambios", description: "Descarga el PDF antes de cambiar de herramienta para conservar lo que has escrito." }); } }} className="ml-2 font-semibold text-accent underline">Rellenar formulario</a>
          </div>}
          <div className="flex shrink-0 items-center justify-between gap-2 px-1 pb-2">
            <span className="min-w-0 truncate text-[0.875rem] font-semibold text-ink-soft">{file.name}</span>
            <div className="flex shrink-0 items-center gap-1">
              <button
                type="button"
                onClick={() => { setPageIndex((i) => Math.max(0, i - 1)); setSelectedTextId(null); }}
                disabled={pageIndex === 0 || isRunning || isUploading}
                aria-label="Página anterior"
                className="flex size-8 items-center justify-center rounded-control text-ink-soft transition-colors hover:bg-surface-sunken hover:text-ink disabled:opacity-30"
              >
                <ChevronLeft className="size-4" />
              </button>
              <span className="min-w-[4rem] text-center text-[0.8125rem] font-semibold text-muted">
                {pageIndex + 1} / {pages.length}
              </span>
              <button
                type="button"
                onClick={() => { setPageIndex((i) => Math.min(pages.length - 1, i + 1)); setSelectedTextId(null); }}
                disabled={pageIndex === pages.length - 1 || isRunning || isUploading}
                aria-label="Página siguiente"
                className="flex size-8 items-center justify-center rounded-control text-ink-soft transition-colors hover:bg-surface-sunken hover:text-ink disabled:opacity-30"
              >
                <ChevronRight className="size-4" />
              </button>
              <button
                type="button"
                onClick={clearFile}
                disabled={isRunning}
                aria-label="Cerrar documento"
                className="ml-1 flex size-8 items-center justify-center rounded-control text-ink-soft transition-colors hover:bg-surface-sunken hover:text-ink"
              >
                <X className="size-4" />
              </button>
            </div>
          </div>
          <div className="relative min-h-0 flex-1">
            <div className="max-h-[55dvh] min-h-0 overflow-auto rounded-[0.75rem] bg-surface-sunken p-3 pb-20 lg:h-full lg:max-h-none lg:p-5 lg:pb-20" aria-label="Lienzo del PDF" role="region" tabIndex={0}>
              <div className="mx-auto shadow-lift" style={{ width: `${zoom * 100}%`, maxWidth: `${760 * zoom}px` }}>
                <EditorStage
                  key={pageIndex}
                  page={current}
                  pageIndex={pageIndex}
                  tool={activeTool}
                  color={color}
                  fill={fill}
                  size={size}
                  strokeWidth={strokeWidth}
                  activeSignature={activeAsset}
                  annotations={pageAnnotations}
                  onAdd={addAnnotation}
                  onSetText={setText}
                  onDelete={deleteAnnotation}
                  onUpdateRect={updateAnnotationRect}
                  onSelectText={selectText}
                  disabled={isRunning}
                  textInputRef={textInputRef}
                />
              </div>
            </div>
            <div role="group" aria-label="Zoom del PDF" className="glass absolute bottom-3 right-3 z-20 flex items-center gap-1 rounded-control p-1 shadow-lift [--glass-alpha:0.95]">
              <button type="button" aria-label="Alejar PDF" disabled={zoom <= 0.5 || isRunning} onClick={() => setZoom((value) => Math.max(0.5, value - 0.25))} className="flex size-11 items-center justify-center rounded-control text-ink transition-colors hover:bg-surface-sunken disabled:opacity-40">
                <Minus className="size-4" />
              </button>
              <button type="button" aria-label="Restablecer zoom al 100%" disabled={isRunning} onClick={() => setZoom(1)} className="min-h-11 min-w-16 rounded-control px-2 text-sm font-semibold text-ink transition-colors hover:bg-surface-sunken">
                <span aria-live="polite">{Math.round(zoom * 100)}%</span>
              </button>
              <button type="button" aria-label="Acercar PDF" disabled={zoom >= 3 || isRunning} onClick={() => setZoom((value) => Math.min(3, value + 0.25))} className="flex size-11 items-center justify-center rounded-control text-ink transition-colors hover:bg-surface-sunken disabled:opacity-40">
                <Plus className="size-4" />
              </button>
            </div>
          </div>
        </div>
      }
      aside={
        <EditorToolbar
          tool={activeTool}
          onTool={(next) => { setActiveTool(next); setSelectedTextId(null); }}
          color={color}
          onColor={updateColor}
          fill={fill}
          onFill={setFill}
          size={size}
          onSize={updateSize}
          strokeWidth={strokeWidth}
          onStrokeWidth={setStrokeWidth}
          fieldSelected={selectedText?.kind === "field"}
          signatures={signatures}
          activeSignature={activeSignature}
          onUploadSignature={uploadSignature}
          onActiveSignature={(index) => {
            setActiveSignature(index);
            setActiveTool("signature");
          }}
          changeCount={annotations.length}
          onUndo={undo}
          onSave={() => void handleSave()}
          isSaving={isRunning}
          isUploading={isUploading}
        />
      }
    />
  );
}
