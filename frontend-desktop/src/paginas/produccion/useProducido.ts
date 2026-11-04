import { useEffect, useState } from "react";
import { ErrorDeApi } from "../../api/cliente";
import { producidoDelPeriodo } from "../../api/produccionPlanta";
import type { Producido } from "../../api/produccionPlanta";

type Guardado = { periodo: string; ok: true; datos: Producido[] } | { periodo: string; ok: false; error: unknown };

export type ProducidoDelMes = { estado: "cargando" } | { estado: "listo"; datos: Producido[] } | { estado: "error"; error: unknown };

// Las toneladas producidas en el mes (las suma el servidor: m³ por densidad). Sin mes válido (`periodo` null) no pide
// nada. Un 401 avisa a `alExpirar`.
export function useProducido(periodo: string | null, alExpirar: () => void): ProducidoDelMes {
  const [guardado, setGuardado] = useState<Guardado | null>(null);

  useEffect(() => {
    if (periodo === null) return;
    const control = new AbortController();
    producidoDelPeriodo(periodo, control.signal).then(
      (datos) => setGuardado({ periodo, ok: true, datos }),
      (error: unknown) => {
        if (control.signal.aborted) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        setGuardado({ periodo, ok: false, error });
      },
    );
    return () => control.abort();
  }, [periodo, alExpirar]);

  if (!guardado || guardado.periodo !== periodo) return { estado: "cargando" };
  return guardado.ok ? { estado: "listo", datos: guardado.datos } : { estado: "error", error: guardado.error };
}
