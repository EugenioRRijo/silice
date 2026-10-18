import { useEffect, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";

// Estado de un GET de solo lectura. `sin_permiso` (403) y `no_disponible` (404) no son errores de la persona:
// el bloque que los recibe decide como decirlo.
export type Carga<T> =
  | { estado: "cargando" }
  | { estado: "listo"; datos: T }
  | { estado: "sin_permiso" }
  | { estado: "no_disponible" }
  | { estado: "error"; error: unknown };

// Pide `ruta` al montarse. Un 401 avisa a `alExpirar` (la sesion vencio) y queda como error.
export function useCarga<T>(ruta: string, alExpirar: () => void): Carga<T> {
  const [carga, setCarga] = useState<{ ruta: string; valor: Carga<T> } | null>(null);

  useEffect(() => {
    let vigente = true;
    pedir<T>(ruta).then(
      (datos) => {
        if (vigente) setCarga({ ruta, valor: { estado: "listo", datos } });
      },
      (error: unknown) => {
        if (!vigente) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        let valor: Carga<T> = { estado: "error", error };
        if (error instanceof ErrorDeApi && error.estado === 403) valor = { estado: "sin_permiso" };
        if (error instanceof ErrorDeApi && error.estado === 404) valor = { estado: "no_disponible" };
        setCarga({ ruta, valor });
      },
    );
    return () => {
      vigente = false;
    };
  }, [ruta, alExpirar]);

  return carga && carga.ruta === ruta ? carga.valor : { estado: "cargando" };
}
