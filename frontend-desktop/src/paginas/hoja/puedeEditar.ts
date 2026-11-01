import { useAplicacion } from "../../shell/contexto";
import type { BaseAbierta } from "./logica";

// Por qué existe (F4, Tarea 2b; Eugenio, 2026-10-31): quien revisa ve la Hoja en solo lectura. Es una sola regla para todos
// los controles que escriben en la Hoja y en las secciones que la comparten; la Tarea 3 la expone como
// `HojaDeLaObra.puedeEditar`. Sin permiso los controles que escriben no se pintan (no se dejan deshabilitados). La API
// vuelve a exigir `editar_hoja` en cada escritura: esto solo evita ofrecer lo que daría 403.
export function puedeEditarLaHoja(acciones: readonly string[], base: Pick<BaseAbierta, "solo_lectura"> | null): boolean {
  return acciones.includes("editar_hoja") && base?.solo_lectura !== true;
}

// La misma regla con las acciones de la sesión.
export function usePuedeEditarLaHoja(base: Pick<BaseAbierta, "solo_lectura"> | null): boolean {
  const { sesion } = useAplicacion();
  return puedeEditarLaHoja(sesion.acciones, base);
}
