import {
  type Announcements,
  DndContext,
  type DragEndEvent,
  KeyboardSensor,
  MouseSensor,
  TouchSensor,
  type UniqueIdentifier,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { SortableContext, arrayMove, rectSortingStrategy, sortableKeyboardCoordinates, useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import { cx } from "../../lib/cx";
import type { EditablePage } from "../../lib/pageEditor";
import type { PageEditorMode } from "../../tools/types";
import { PageCard } from "./PageCard";

const GRID = "grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 2xl:grid-cols-5";
const SKELETON_CARDS = 8;

interface PageGridProps {
  pages: EditablePage[];
  mode: PageEditorMode;
  disabled: boolean;
  onActivate: (id: string) => void;
  onRotate: (id: string, delta: 90 | -90) => void;
  onToggleRemoved: (id: string) => void;
  onReorder: (pages: EditablePage[]) => void;
}

export function PageGrid(props: PageGridProps) {
  const { pages, mode, onReorder: _onReorder, ...cardProps } = props;
  if (mode === "organize") return <SortablePageGrid {...props} />;

  return (
    <ul className={GRID}>
      {pages.map((page, index) => (
        <li key={page.id}>
          <PageCard page={page} position={index + 1} mode={mode} {...cardProps} />
        </li>
      ))}
    </ul>
  );
}

export function PageGridSkeleton() {
  return (
    <ul aria-hidden className={GRID}>
      {Array.from({ length: SKELETON_CARDS }, (_, index) => (
        <li key={index} className="aspect-[3/4] rounded-[0.75rem] bg-line/40 motion-safe:animate-pulse" />
      ))}
    </ul>
  );
}

// ——— Reordenar arrastrando (ratón, táctil con pulsación larga y teclado) ———

const pageName = (id: UniqueIdentifier) => `la página ${String(id).replace("p-", "")}`;

const ANNOUNCEMENTS: Announcements = {
  onDragStart: ({ active }) => `Has tomado ${pageName(active.id)}.`,
  onDragOver: ({ active, over }) =>
    over ? `${pageName(active.id)} está sobre ${pageName(over.id)}.` : `${pageName(active.id)} no está sobre ninguna página.`,
  onDragEnd: ({ active, over }) =>
    over ? `Has soltado ${pageName(active.id)} en el lugar de ${pageName(over.id)}.` : `Has soltado ${pageName(active.id)}.`,
  onDragCancel: ({ active }) => `Movimiento cancelado: ${pageName(active.id)} vuelve a su sitio.`,
};

const SCREEN_READER_INSTRUCTIONS = {
  draggable: "Pulsa espacio para tomar la página, muévela con las flechas y vuelve a pulsar espacio para soltarla.",
};

function SortablePageGrid({ pages, mode, disabled, onReorder, ...cardProps }: PageGridProps) {
  const sensors = useSensors(
    useSensor(MouseSensor, { activationConstraint: { distance: 6 } }),
    // En pantallas táctiles hace falta mantener pulsado: así el dedo puede seguir desplazando la lista.
    useSensor(TouchSensor, { activationConstraint: { delay: 220, tolerance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const handleDragEnd = ({ active, over }: DragEndEvent) => {
    if (!over || active.id === over.id) return;
    const from = pages.findIndex((page) => page.id === active.id);
    const to = pages.findIndex((page) => page.id === over.id);
    if (from >= 0 && to >= 0) onReorder(arrayMove(pages, from, to));
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
      accessibility={{ announcements: ANNOUNCEMENTS, screenReaderInstructions: SCREEN_READER_INSTRUCTIONS }}
    >
      <SortableContext items={pages.map((page) => page.id)} strategy={rectSortingStrategy} disabled={disabled}>
        <ul className={GRID}>
          {pages.map((page, index) => (
            <SortablePage key={page.id} page={page} position={index + 1} mode={mode} disabled={disabled} {...cardProps} />
          ))}
        </ul>
      </SortableContext>
    </DndContext>
  );
}

type SortablePageProps = Omit<PageGridProps, "pages" | "onReorder"> & { page: EditablePage; position: number };

function SortablePage({ page, ...cardProps }: SortablePageProps) {
  const { attributes, listeners, setNodeRef, setActivatorNodeRef, transform, transition, isDragging } = useSortable({
    id: page.id,
  });

  return (
    <li
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cx(isDragging && "relative z-10")}
    >
      <PageCard
        page={page}
        {...cardProps}
        isDragging={isDragging}
        dragHandle={{ ref: setActivatorNodeRef, attributes, listeners }}
      />
    </li>
  );
}
