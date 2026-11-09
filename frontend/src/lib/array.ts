/** Devuelve una copia con el elemento movido, o la MISMA lista si el movimiento no es válido
 *  (así `setState` no provoca un render inútil). */
export function moveItem<T>(list: T[], from: number, to: number): T[] {
  const item = list[from];
  if (item === undefined || from === to || to < 0 || to >= list.length) return list;

  const next = list.filter((_, index) => index !== from);
  next.splice(to, 0, item);
  return next;
}
