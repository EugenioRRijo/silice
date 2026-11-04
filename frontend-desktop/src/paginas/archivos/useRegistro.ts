import { useCallback, useEffect, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { rutaDeImportaciones } from "./logica";
import type { ImportacionesRespuesta } from "./logica";

export type CargaDelRegistro =
  | { estado: "cargando" }
  | { estado: "listo"; datos: ImportacionesRespuesta }
  | { estado: "error"; error: unknown };

// Por qué existe (Tarea 11 del plan F4): el registro de importaciones de la obra (`GET /v1/hoja/importaciones`, Tarea 10),
// que Archivos y planos vuelve a leer tras cada fusión. A diferencia de `useCarga`, al volver a leer conserva lo que ya se
// veía hasta que llega la respuesta nueva (la tabla no parpadea). Solo lo usa la pantalla de Archivos y planos.
export function useRegistro(proyecto: string, alExpirar: () => void): { carga: CargaDelRegistro; recargar: () => void } {
  const [leida, setLeida] = useState<{ proyecto: string; carga: CargaDelRegistro } | null>(null);
  const [vez, setVez] = useState(0);
  const recargar = useCallback(() => setVez((n) => n + 1), []);

  useEffect(() => {
    let vigente = true;
    pedir<ImportacionesRespuesta>(rutaDeImportaciones(proyecto)).then(
      (datos) => {
        if (vigente) setLeida({ proyecto, carga: { estado: "listo", datos } });
      },
      (error: unknown) => {
        if (!vigente) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        setLeida({ proyecto, carga: { estado: "error", error } });
      },
    );
    return () => {
      vigente = false;
    };
  }, [proyecto, vez, alExpirar]);

  return { carga: leida !== null && leida.proyecto === proyecto ? leida.carga : { estado: "cargando" }, recargar };
}
