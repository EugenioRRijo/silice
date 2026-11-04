import { useEffect } from "react";

// Formularios con cambios sin guardar que viven en el navegador (diseno de modulos §12.5): si la persona sale de la
// pantalla por un control de Silice (el sidebar, la barra, un boton de la mesa), `confirmarSalida` (salida.ts) le
// pregunta antes. Solo en memoria (RT-9). Cada registro es una clave propia: dos formularios de la misma pantalla son dos
// registros, y la pantalla sale una vez.
// El borrador de la Hoja vive en el servidor: dentro de una obra lo registra `ProveedorDeLaHoja` (Tarea 3 del plan F4)
// como trabajo `EnElServidor`: pasar a otra seccion de la misma obra que comparte el borrador no lo pierde, y salir de la
// obra tampoco (se ofrece retomarlo al volver), salvo al cambiar de carpeta.
export interface EnElServidor {
  // Los destinos que siguen usando este trabajo (no se pregunta al ir alli).
  conservaAlIrA: (destino: string) => boolean;
}

interface Registro {
  id: string;
  // null = vive solo en el navegador y se pierde al salir.
  enElServidor: EnElServidor | null;
}

const registro = new Map<symbol, Registro>();

// `id` es el id de la pantalla en rutas.ts (su titulo es el que lee el dialogo). Se quita al limpiarse o al desmontar.
// `enElServidor` debe ser estable (useMemo): si cambia, el registro se rehace.
export function useFormularioSucio(id: string, sucio: boolean, enElServidor: EnElServidor | null = null): void {
  useEffect(() => {
    if (!sucio) return;
    const clave = Symbol(id);
    registro.set(clave, { id, enElServidor });
    return () => {
      registro.delete(clave);
    };
  }, [id, sucio, enElServidor]);
}

// Los registros que cuentan al ir a `destino` (null = a cualquier sitio).
function pendientes(destino: string | null): Registro[] {
  return [...registro.values()].filter((r) => destino === null || r.enElServidor === null || !r.enElServidor.conservaAlIrA(destino));
}

// Las pantallas con algun formulario sucio que cuenta al ir a `destino`, en el orden en que se ensuciaron, sin repetir.
export function formulariosSucios(destino: string | null = null): string[] {
  return [...new Set(pendientes(destino).map((r) => r.id))];
}

// Si todo lo que cuenta al ir a `destino` vive en el servidor (se retoma al volver): el dialogo no habla de perderlo.
export function soloTrabajoEnElServidor(destino: string | null = null): boolean {
  const lista = pendientes(destino);
  return lista.length > 0 && lista.every((r) => r.enElServidor !== null);
}

// «Salir y descartar»: lo que habia se da por perdido.
export function olvidarFormularios(): void {
  registro.clear();
}
