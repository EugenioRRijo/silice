import { useCallback, useContext, useEffect, useState } from "react";
import { ErrorDeApi, pedir } from "../api/cliente";
import type { ObraDeCarpetaRespuesta, ObrasTodasRespuesta } from "../api/tipos";
import { ContextoAplicacion } from "../shell/contexto";

export type ObraDeCarpeta = ObraDeCarpetaRespuesta;

export interface ObrasCargadas {
  obras: ObraDeCarpeta[];
  // La carpeta abierta en la sesión; null si es la de la empresa.
  carpetaActual: string | null;
  estado: "cargando" | "lista" | "error";
  recargar: () => void;
}

// Las obras de todas las carpetas a las que la cuenta tiene acceso (`GET /v1/obras/todas`, Tarea 3 del plan del marco):
// con `cambiar_caso` son las de todas las carpetas; sin él, solo las de la abierta. La barra lateral y el buscador la
// comparten. Mientras recarga conserva la lista anterior y el estado vuelve a «cargando».
export function useObras(): ObrasCargadas {
  const alExpirar = useContext(ContextoAplicacion)?.alExpirar;
  const [intento, setIntento] = useState(0);
  const [datos, setDatos] = useState<{ obras: ObraDeCarpeta[]; carpetaActual: string | null }>({
    obras: [],
    carpetaActual: null,
  });
  const [estado, setEstado] = useState<ObrasCargadas["estado"]>("cargando");

  useEffect(() => {
    let vigente = true;
    pedir<ObrasTodasRespuesta>("/v1/obras/todas")
      .then((r) => {
        if (!vigente) return;
        if (!Array.isArray(r?.obras)) {
          setEstado("error");
          return;
        }
        setDatos({ obras: r.obras, carpetaActual: r.carpeta_actual ?? null });
        setEstado("lista");
      })
      .catch((e: unknown) => {
        if (!vigente) return;
        if (e instanceof ErrorDeApi && e.estado === 401) alExpirar?.();
        setEstado("error");
      });
    return () => {
      vigente = false;
    };
  }, [intento, alExpirar]);

  const recargar = useCallback(() => {
    setEstado("cargando");
    setIntento((n) => n + 1);
  }, []);
  return { obras: datos.obras, carpetaActual: datos.carpetaActual, estado, recargar };
}
