import { useEffect, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";

// Estado de un GET de solo lectura. `sin_permiso` (403) y `no_disponible` (404) no son errores de la persona:
// el bloque que los recibe decide como decirlo.
export type Carga<T> =
  | { estado: "cargando" }
  | { estado: "listo"; datos: T }
  | { estado: "sin_permiso"; error: unknown }
  | { estado: "no_disponible"; error: unknown }
  | { estado: "error"; error: unknown };

// Pide `ruta` al montarse. Con `ruta` null no pide nada (la cuenta no tiene la accion que el recurso exige: la API
// daria 403 y el navegador lo registraria como error) y queda en `sin_permiso`. Un 401 avisa a `alExpirar` (la sesion vencio) y queda como error.
export function useCarga<T>(ruta: string | null, alExpirar: () => void): Carga<T> {
  const [carga, setCarga] = useState<{ ruta: string; valor: Carga<T> } | null>(null);

  useEffect(() => {
    if (ruta === null) return;
    let vigente = true;
    pedir<T>(ruta).then(
      (datos) => {
        if (vigente) setCarga({ ruta, valor: { estado: "listo", datos } });
      },
      (error: unknown) => {
        if (!vigente) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        let valor: Carga<T> = { estado: "error", error };
        if (error instanceof ErrorDeApi && error.estado === 403) valor = { estado: "sin_permiso", error };
        if (error instanceof ErrorDeApi && error.estado === 404) valor = { estado: "no_disponible", error };
        setCarga({ ruta, valor });
      },
    );
    return () => {
      vigente = false;
    };
  }, [ruta, alExpirar]);

  if (ruta === null) return { estado: "sin_permiso", error: null };
  return carga && carga.ruta === ruta ? carga.valor : { estado: "cargando" };
}
