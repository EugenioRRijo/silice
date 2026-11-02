import { useEffect, useState } from "react";
import { ErrorDeApi } from "../../api/cliente";
import { materialesDeArenera, recetaVigente } from "../../api/produccionPlanta";
import type { RecetaRespuesta } from "../../api/produccionPlanta";

export interface Mezcla {
  codigo: string;
  nombre: string;
  receta: RecetaRespuesta;
}

type Guardado = { fecha: string; ok: true; datos: Mezcla[] } | { fecha: string; ok: false; error: unknown };

export type MezclasConReceta = { estado: "cargando" } | { estado: "listo"; datos: Mezcla[] } | { estado: "error"; error: unknown };

// Los productos con receta vigente en `fecha`. El servidor no lista recetas, así que se pregunta por cada material activo
// de la arenera: un 404 dice «sin receta» y ese producto no se ofrece; cualquier otro fallo detiene la lista. Un 401 avisa
// a `alExpirar`. Sin fecha válida (`null`) no pide nada.
export function useMezclas(fecha: string | null, alExpirar: () => void): MezclasConReceta {
  const [guardado, setGuardado] = useState<Guardado | null>(null);

  useEffect(() => {
    if (fecha === null) return;
    const control = new AbortController();
    const leer = async (): Promise<Mezcla[]> => {
      const materiales = (await materialesDeArenera(control.signal)).filter((m) => m.activo);
      const hallados = await Promise.all(
        materiales.map(async (m): Promise<Mezcla | null> => {
          try {
            return { codigo: m.codigo, nombre: m.nombre, receta: await recetaVigente(m.codigo, fecha, control.signal) };
          } catch (razon) {
            if (razon instanceof ErrorDeApi && razon.estado === 404) return null;
            throw razon;
          }
        }),
      );
      return hallados.filter((m): m is Mezcla => m !== null);
    };
    leer().then(
      (datos) => setGuardado({ fecha, ok: true, datos }),
      (error: unknown) => {
        if (control.signal.aborted) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        setGuardado({ fecha, ok: false, error });
      },
    );
    return () => control.abort();
  }, [fecha, alExpirar]);

  if (!guardado || guardado.fecha !== fecha) return { estado: "cargando" };
  return guardado.ok ? { estado: "listo", datos: guardado.datos } : { estado: "error", error: guardado.error };
}
