import { useEffect, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";

export type EstadoVista<T> =
  | { estado: "cargando" }
  | { estado: "listo"; datos: T; actualizando: boolean }
  | { estado: "error"; error: unknown };

// Pide una vista de la hoja. Mientras llega la de otra ruta (por ejemplo, otra búsqueda) o una lectura nueva de la misma
// (`recarga` sube tras una edición) deja a la vista la anterior, con `actualizando`, para que la lista no parpadee.
// Un 401 avisa a `alExpirar`.
export function useVista<T>(ruta: string, alExpirar: () => void, recarga = 0): EstadoVista<T> {
  const [res, setRes] = useState<{ ruta: string; recarga: number; datos: T | null; error: unknown } | null>(null);

  useEffect(() => {
    let vigente = true;
    pedir<T>(ruta).then(
      (datos) => {
        if (vigente) setRes({ ruta, recarga, datos, error: null });
      },
      (error: unknown) => {
        if (!vigente) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        setRes({ ruta, recarga, datos: null, error });
      },
    );
    return () => {
      vigente = false;
    };
  }, [ruta, recarga, alExpirar]);

  if (res === null) return { estado: "cargando" };
  if (res.error !== null && res.ruta === ruta && res.recarga === recarga) return { estado: "error", error: res.error };
  if (res.datos !== null) {
    return { estado: "listo", datos: res.datos, actualizando: res.ruta !== ruta || res.recarga !== recarga };
  }
  return { estado: "cargando" };
}
