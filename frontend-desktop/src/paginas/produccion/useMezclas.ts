import { useEffect, useState } from "react";
import { ErrorDeApi } from "../../api/cliente";
import { materialesDeArenera, recetasVigentes } from "../../api/produccionPlanta";
import type { RecetaRespuesta } from "../../api/produccionPlanta";

export interface Mezcla {
  codigo: string;
  nombre: string;
  receta: RecetaRespuesta;
}

type Guardado = { fecha: string; ok: true; datos: Mezcla[] } | { fecha: string; ok: false; error: unknown };

export type MezclasConReceta = { estado: "cargando" } | { estado: "listo"; datos: Mezcla[] } | { estado: "error"; error: unknown };

// Los productos con receta vigente en `fecha`. El servidor responde en una sola petición las recetas que rigen ese día; se
// ofrecen los materiales activos de la arenera que tienen una (un agregado sin receta no se pregunta ni provoca un 404).
// Cualquier fallo detiene la lista; un 401 avisa a `alExpirar`. Sin fecha válida (`null`) no pide nada.
export function useMezclas(fecha: string | null, alExpirar: () => void): MezclasConReceta {
  const [guardado, setGuardado] = useState<Guardado | null>(null);

  useEffect(() => {
    if (fecha === null) return;
    const control = new AbortController();
    const leer = async (): Promise<Mezcla[]> => {
      const [materiales, recetas] = await Promise.all([materialesDeArenera(control.signal), recetasVigentes(fecha, control.signal)]);
      const porProducto = new Map(recetas.map((r) => [r.producto, r]));
      const hallados: Mezcla[] = [];
      for (const m of materiales) {
        const receta = porProducto.get(m.codigo);
        if (m.activo && receta) hallados.push({ codigo: m.codigo, nombre: m.nombre, receta });
      }
      return hallados;
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
