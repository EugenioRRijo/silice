import type { BaseAbierta } from "./logica";

// Stub del rojo (F4, Tarea 2b): la regla de hoy, en que quien ve la Hoja la edita. El commit siguiente la fija.
export function puedeEditarLaHoja(_acciones: readonly string[], _base: Pick<BaseAbierta, "solo_lectura"> | null): boolean {
  return true;
}
