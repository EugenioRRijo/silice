import { useEffect } from "react";

// Formularios con cambios sin guardar que viven en el navegador (diseno de modulos §12.5): si la persona sale de la
// pantalla por un control de Silice (el sidebar, la barra, un boton de la mesa), `confirmarSalida` (salida.ts) le
// pregunta antes. Solo en memoria (RT-9). Cada registro es una clave propia: dos formularios de la misma pantalla son dos
// registros, y la pantalla sale una vez.
// El borrador de la Hoja vive en el servidor: dentro de una obra lo registra `ProveedorDeLaHoja` (Tarea 3 del plan F4) con
// `conservaAlIrA`, porque pasar a otra seccion de la misma obra que comparte el borrador no lo pierde.
interface Registro {
  id: string;
  // Los destinos a los que se puede ir sin perder este trabajo; null = ninguno.
  conservaAlIrA: ((destino: string) => boolean) | null;
}

const registro = new Map<symbol, Registro>();

// `id` es el id de la pantalla en rutas.ts (su titulo es el que lee el dialogo). Se quita al limpiarse o al desmontar.
// `conservaAlIrA` debe ser estable (useCallback o useMemo): si cambia, el registro se rehace.
export function useFormularioSucio(id: string, sucio: boolean, conservaAlIrA: ((destino: string) => boolean) | null = null): void {
  useEffect(() => {
    if (!sucio) return;
    const clave = Symbol(id);
    registro.set(clave, { id, conservaAlIrA });
    return () => {
      registro.delete(clave);
    };
  }, [id, sucio, conservaAlIrA]);
}

// Las pantallas con algun formulario sucio que se perderia al ir a `destino` (null = a cualquier sitio), en el orden en
// que se ensuciaron, sin repetir.
export function formulariosSucios(destino: string | null = null): string[] {
  const perdidos = [...registro.values()].filter((r) => destino === null || r.conservaAlIrA === null || !r.conservaAlIrA(destino));
  return [...new Set(perdidos.map((r) => r.id))];
}

// «Salir y descartar»: lo que habia se da por perdido.
export function olvidarFormularios(): void {
  registro.clear();
}
