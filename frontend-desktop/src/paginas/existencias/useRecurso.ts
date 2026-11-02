import { useEffect, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";

type Guardado<T> =
  | { ruta: string; version: number; ok: true; datos: T }
  | { ruta: string; version: number; ok: false; error: unknown };

export type Recurso<T> =
  | { estado: "cargando" }
  | { estado: "listo"; datos: T }
  | { estado: "error"; error: unknown };

// Un GET de la arenera. Mientras se pide por primera vez (o se cambia de `ruta`, por ejemplo la fecha) esta
// «cargando»; cuando solo sube `version` (se registro algo y hay que releer) se sigue mostrando lo ultimo que llego
// hasta que llegue lo nuevo, para que la pantalla no parpadee ni pierda el lugar. Un error si vuelve a «cargando»
// al reintentar. Un 401 avisa a `alExpirar` (la sesion vencio); un 403 a `alDenegar` (la cuenta no puede operar la
// arenera): la pagina entera dice entonces que falta el permiso.
export function useRecurso<T>(
  ruta: string,
  version: number,
  alExpirar: () => void,
  alDenegar: () => void,
): Recurso<T> {
  const [guardado, setGuardado] = useState<Guardado<T> | null>(null);

  useEffect(() => {
    let vigente = true;
    pedir<T>(ruta).then(
      (datos) => {
        if (vigente) setGuardado({ ruta, version, ok: true, datos });
      },
      (error: unknown) => {
        if (!vigente) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        if (error instanceof ErrorDeApi && error.estado === 403) alDenegar();
        setGuardado({ ruta, version, ok: false, error });
      },
    );
    return () => {
      vigente = false;
    };
  }, [ruta, version, alExpirar, alDenegar]);

  if (!guardado || guardado.ruta !== ruta) return { estado: "cargando" };
  if (!guardado.ok) return guardado.version === version ? { estado: "error", error: guardado.error } : { estado: "cargando" };
  return { estado: "listo", datos: guardado.datos };
}
