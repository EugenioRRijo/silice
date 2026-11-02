import { useCallback, useEffect, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import type { EstadoDeAprobacion } from "../../comun/aprobacion";
import { useAplicacion } from "../../shell/contexto";

// Por qué existe (Tarea 5 del plan F4): el estado de aprobación de la versión abierta lo necesitan la franja del
// Presupuesto (`FranjaDelPresupuesto`, para saber si toca enviar, corregir o esperar) y, desde la Tarea 6, Versiones, que
// pinta el de cada versión (`useEstadosDeAprobacion`). Sale de `AprobacionDeVersion.tsx`, que se queda con lo que se ve de
// la aprobación y con el diálogo de enviar. Lee `GET /v1/aprobaciones?proyecto=` (api/rutas/aprobaciones.py, Tarea 18): el
// último movimiento de cada versión manda. Las dos lecturas comparten `useLecturaDeAprobaciones`.

const RUTA = "/v1/aprobaciones";

export type Lectura<T> = { estado: "leyendo" } | { estado: "listo"; datos: T } | { estado: "fallo" };
export type LecturaDeAprobacion = Lectura<EstadoDeAprobacion | null>;
export type LecturaDeEstados = Lectura<Record<string, EstadoDeAprobacion> | null>;

// La respuesta trae `versiones` como objeto: si no (un servidor sin la ruta), no hay nada que decir.
function estadosDe(respuesta: unknown): Record<string, EstadoDeAprobacion> | null {
  const versiones = (respuesta as { versiones?: unknown } | null | undefined)?.versiones;
  if (typeof versiones !== "object" || versiones === null) return null;
  const validos = Object.entries(versiones as Record<string, EstadoDeAprobacion | undefined>).filter(
    (par): par is [string, EstadoDeAprobacion] => typeof par[1]?.estado === "string",
  );
  return Object.fromEntries(validos);
}

function estadoDe(respuesta: unknown, version: string): EstadoDeAprobacion | null {
  return estadosDe(respuesta)?.[version] ?? null;
}

// Pide la respuesta entera si `pedirla`; `clave` dice cuándo una respuesta ya no vale (otra obra u otra versión) y se vuelve
// a «leyendo». Cualquier error es «fallo» (un 401 avisa además al marco). `recargar` vuelve a leer y, mientras llega, se
// queda con lo que ya había (no parpadea).
function useLecturaDeAprobaciones(
  proyecto: string,
  pedirla: boolean,
  clave: string,
): { lectura: Lectura<unknown>; recargar: () => void } {
  const { alExpirar } = useAplicacion();
  const [intento, setIntento] = useState(0);
  const [resultado, setResultado] = useState<{ clave: string; lectura: Lectura<unknown> } | null>(null);

  useEffect(() => {
    if (!pedirla) return;
    let vigente = true;
    pedir<unknown>(`${RUTA}?${new URLSearchParams({ proyecto }).toString()}`).then(
      (r) => {
        if (vigente) setResultado({ clave, lectura: { estado: "listo", datos: r } });
      },
      (error: unknown) => {
        if (!vigente) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        setResultado({ clave, lectura: { estado: "fallo" } });
      },
    );
    return () => {
      vigente = false;
    };
  }, [proyecto, pedirla, clave, intento, alExpirar]);

  const recargar = useCallback(() => setIntento((n) => n + 1), []);
  const lectura: Lectura<unknown> = resultado !== null && resultado.clave === clave ? resultado.lectura : { estado: "leyendo" };
  return { lectura, recargar };
}

// Sin versión (el borrador en blanco) no se pide nada: listo, sin estado. Sin saber el estado, la franja no ofrece enviar.
// Cambiar de obra o de versión empieza de cero («leyendo»).
export function useAprobacionDeVersion(
  proyecto: string,
  version: string | null,
): LecturaDeAprobacion & { recargar: () => void } {
  const { lectura, recargar } = useLecturaDeAprobaciones(proyecto, version !== null, JSON.stringify([proyecto, version]));
  if (version === null) return { estado: "listo", datos: null, recargar };
  if (lectura.estado !== "listo") return { ...lectura, recargar };
  return { estado: "listo", datos: estadoDe(lectura.datos, version), recargar };
}

// El estado de cada versión de la obra (Versiones, Tarea 6): `datos` es null si la respuesta no trae `versiones`.
export function useEstadosDeAprobacion(proyecto: string): LecturaDeEstados {
  const { lectura } = useLecturaDeAprobaciones(proyecto, true, proyecto);
  if (lectura.estado !== "listo") return lectura;
  return { estado: "listo", datos: estadosDe(lectura.datos) };
}
