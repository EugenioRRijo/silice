import { useEffect, useState } from "react";
import { ErrorDeApi } from "../../api/cliente";
import { listarCostos } from "../../api/costos";
import type { CostoRespuesta } from "../../api/costos";

type Guardado =
  | { clave: string; version: number; ok: true; datos: CostoRespuesta[] }
  | { clave: string; version: number; ok: false; error: unknown };

export type Costos =
  | { estado: "cargando" }
  | { estado: "listo"; datos: CostoRespuesta[] }
  | { estado: "error"; error: unknown };

// Los costos de un mes. Al cambiar de mes o del filtro de anulados queda «cargando»; cuando solo sube `version` (se
// registró o anuló algo) se sigue mostrando la lista anterior hasta que llegue la nueva: la fila no desaparece por
// adelantado. Sin mes válido (`periodo` null) no pide nada. Un 401 avisa a `alExpirar`.
export function useCostos(periodo: string | null, incluirAnulados: boolean, version: number, alExpirar: () => void): Costos {
  const [guardado, setGuardado] = useState<Guardado | null>(null);
  const clave = `${periodo}|${incluirAnulados}`;

  useEffect(() => {
    if (periodo === null) return;
    const control = new AbortController();
    listarCostos(periodo, incluirAnulados, control.signal).then(
      (datos) => setGuardado({ clave, version, ok: true, datos }),
      (error: unknown) => {
        if (control.signal.aborted) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        setGuardado({ clave, version, ok: false, error });
      },
    );
    return () => control.abort();
  }, [periodo, incluirAnulados, version, clave, alExpirar]);

  if (!guardado || guardado.clave !== clave) return { estado: "cargando" };
  if (!guardado.ok) return guardado.version === version ? { estado: "error", error: guardado.error } : { estado: "cargando" };
  return { estado: "listo", datos: guardado.datos };
}
