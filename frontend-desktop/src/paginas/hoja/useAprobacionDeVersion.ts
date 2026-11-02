import { useCallback, useEffect, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import type { EstadoDeAprobacion } from "../../comun/aprobacion";
import { useAplicacion } from "../../shell/contexto";

// Por qué existe (Tarea 5 del plan F4): el estado de aprobación de la versión abierta lo necesitan la franja del
// Presupuesto (`FranjaDelPresupuesto`, para saber si toca enviar, corregir o esperar) y, desde la Tarea 6, Versiones. Sale de
// `AprobacionDeVersion.tsx`, que se queda con lo que se ve de la aprobación y con el diálogo de enviar. Lee
// `GET /v1/aprobaciones?proyecto=` (api/rutas/aprobaciones.py, Tarea 18): el último movimiento de cada versión manda.

const RUTA = "/v1/aprobaciones";

export type LecturaDeAprobacion =
  | { estado: "leyendo" }
  | { estado: "listo"; datos: EstadoDeAprobacion | null }
  | { estado: "fallo" };

// La respuesta trae `versiones` como objeto: si no (un servidor sin la ruta), no hay nada que decir.
function estadoDe(respuesta: unknown, version: string): EstadoDeAprobacion | null {
  const versiones = (respuesta as { versiones?: unknown } | null | undefined)?.versiones;
  if (typeof versiones !== "object" || versiones === null) return null;
  const estado = (versiones as Record<string, EstadoDeAprobacion | undefined>)[version];
  return estado && typeof estado.estado === "string" ? estado : null;
}

// Sin versión (el borrador en blanco) no se pide nada: listo, sin estado. Cualquier error es «fallo» (un 401 avisa además
// al marco): sin saber el estado, la franja no ofrece enviar. `recargar` vuelve a leer y, mientras llega, se queda con lo
// que ya había (no parpadea); cambiar de obra o de versión empieza de cero («leyendo»).
export function useAprobacionDeVersion(
  proyecto: string,
  version: string | null,
): LecturaDeAprobacion & { recargar: () => void } {
  const { alExpirar } = useAplicacion();
  const [intento, setIntento] = useState(0);
  const clave = JSON.stringify([proyecto, version]);
  const [resultado, setResultado] = useState<{ clave: string; lectura: LecturaDeAprobacion } | null>(null);

  useEffect(() => {
    if (version === null) return;
    let vigente = true;
    const de = JSON.stringify([proyecto, version]);
    pedir<unknown>(`${RUTA}?${new URLSearchParams({ proyecto }).toString()}`).then(
      (r) => {
        if (vigente) setResultado({ clave: de, lectura: { estado: "listo", datos: estadoDe(r, version) } });
      },
      (error: unknown) => {
        if (!vigente) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        setResultado({ clave: de, lectura: { estado: "fallo" } });
      },
    );
    return () => {
      vigente = false;
    };
  }, [proyecto, version, intento, alExpirar]);

  const recargar = useCallback(() => setIntento((n) => n + 1), []);
  const lectura: LecturaDeAprobacion =
    version === null
      ? { estado: "listo", datos: null }
      : resultado !== null && resultado.clave === clave
        ? resultado.lectura
        : { estado: "leyendo" };
  return { ...lectura, recargar };
}
