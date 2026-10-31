import { useCallback, useEffect, useState } from "react";
import { ErrorDeApi } from "../../api/cliente";
import { tramosDeVersion } from "../../api/vial";
import type { TramosDeVersion } from "../../api/vial";

export type EstadoDeTramos = { estado: "cargando" } | { estado: "listo"; datos: TramosDeVersion } | { estado: "error"; error: unknown };

// Los tramos de una versión. Mientras llega la lectura de otra versión se dice «cargando» (nunca se muestran los de la
// anterior); `reemplazar` pone lo que devolvió una importación sin volver a pedir. Un 401 avisa a la aplicación.
export function useTramos(
  proyecto: string | null,
  version: string | null,
  alExpirar: () => void,
): { carga: EstadoDeTramos; reemplazar: (datos: TramosDeVersion) => void } {
  const clave = proyecto !== null && version !== null ? JSON.stringify([proyecto, version]) : null;
  const [guardado, setGuardado] = useState<{ clave: string; valor: EstadoDeTramos } | null>(null);

  useEffect(() => {
    if (clave === null) return;
    const [nombre, codigo] = JSON.parse(clave) as [string, string];
    const aborto = new AbortController();
    tramosDeVersion(nombre, codigo, aborto.signal).then(
      (datos) => setGuardado({ clave, valor: { estado: "listo", datos } }),
      (error: unknown) => {
        if (aborto.signal.aborted) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        setGuardado({ clave, valor: { estado: "error", error } });
      },
    );
    return () => aborto.abort();
  }, [clave, alExpirar]);

  const reemplazar = useCallback(
    (datos: TramosDeVersion) => {
      if (clave !== null) setGuardado({ clave, valor: { estado: "listo", datos } });
    },
    [clave],
  );

  const carga: EstadoDeTramos = guardado !== null && guardado.clave === clave ? guardado.valor : { estado: "cargando" };
  return { carga, reemplazar };
}
