import { useCallback, useContext, useEffect, useState } from "react";
import { ErrorDeApi, pedir } from "../api/cliente";
import type { ObraFilaRespuesta } from "../api/tipos";
import { ContextoAplicacion } from "../shell/contexto";

export type FichaDeLaObra = { estado: "cargando" } | { estado: "lista"; obra: ObraFilaRespuesta } | { estado: "sin_dato" };

type Leida = Exclude<FichaDeLaObra, { estado: "cargando" }>;

// La ficha de la obra abierta: su fila de `GET /v1/obras/resumen` (Tarea 1 del plan F4; la cabecera y el Resumen la
// comparten). La ruta calcula todas las obras de la carpeta y aquí se queda una (pregunta 2 del plan). La carpeta ya
// está fijada en la sesión cuando la obra está «lista». Un 403, un error o la falta de fila dan `sin_dato`: la sección
// se monta igual, sin estado. Un 401 llama a `alExpirar`. La lectura se repite al cambiar de obra (o de carpeta, porque
// dos carpetas pueden tener el mismo número de obra) o al llamar a `recargar`, nunca al cambiar de sección. Mientras
// llega la de otra obra no se enseña la anterior.
export function useFichaDeLaObra(obraId: number, carpeta: string | null): FichaDeLaObra & { recargar: () => void } {
  const alExpirar = useContext(ContextoAplicacion)?.alExpirar;
  const [intento, setIntento] = useState(0);
  const [leida, setLeida] = useState<{ clave: string; ficha: Leida } | null>(null);
  const clave = JSON.stringify([carpeta, obraId]);

  useEffect(() => {
    let vigente = true;
    pedir<{ obras?: ObraFilaRespuesta[] }>("/v1/obras/resumen")
      .then((r) => {
        if (!vigente) return;
        const fila = Array.isArray(r?.obras) ? r.obras.find((o) => o.codigo === String(obraId)) : undefined;
        // Una fila sin el texto de la etapa no se puede decir en palabras: se trata como si faltara.
        setLeida({ clave, ficha: typeof fila?.etapa_texto === "string" ? { estado: "lista", obra: fila } : { estado: "sin_dato" } });
      })
      .catch((e: unknown) => {
        if (!vigente) return;
        if (e instanceof ErrorDeApi && e.estado === 401) alExpirar?.();
        setLeida({ clave, ficha: { estado: "sin_dato" } });
      });
    return () => {
      vigente = false;
    };
  }, [clave, obraId, intento, alExpirar]);

  const recargar = useCallback(() => setIntento((n) => n + 1), []);
  const ficha: FichaDeLaObra = leida?.clave === clave ? leida.ficha : { estado: "cargando" };
  return { ...ficha, recargar };
}
