import { useCallback, useContext, useEffect, useState } from "react";
import { ErrorDeApi, pedir } from "../api/cliente";
import type { ObraDeCarpetaRespuesta, ObrasTodasRespuesta } from "../api/tipos";
import { ContextoAplicacion } from "../shell/contexto";

export type ObraDeCarpeta = ObraDeCarpetaRespuesta;

export interface ObrasCargadas {
  obras: ObraDeCarpeta[];
  // La carpeta abierta en la sesión; null si es la de la empresa.
  carpetaActual: string | null;
  // «sin_permiso»: la cuenta no lee obras (sin `leer_proyecto`): no se piden y no hay nada que mostrar.
  estado: "cargando" | "lista" | "error" | "sin_permiso";
  recargar: () => void;
}

// Las obras de todas las carpetas a las que la cuenta tiene acceso (`GET /v1/obras/todas`, Tarea 3 del plan del marco):
// con `cambiar_caso` son las de todas las carpetas; sin él, solo las de la abierta. La barra lateral y el buscador la
// comparten. Mientras recarga conserva la lista anterior y el estado vuelve a «cargando». Sin `leer_proyecto` la API
// contestaría 403: no se pide (VB-9). El marco, que la usa fuera de su propio contexto, da las acciones de la sesión.
export function useObras(acciones?: readonly string[]): ObrasCargadas {
  const aplicacion = useContext(ContextoAplicacion);
  const alExpirar = aplicacion?.alExpirar;
  const deLaCuenta = acciones ?? aplicacion?.sesion.acciones;
  const puedeLeer = deLaCuenta === undefined || deLaCuenta.includes("leer_proyecto");
  const [intento, setIntento] = useState(0);
  const [datos, setDatos] = useState<{ obras: ObraDeCarpeta[]; carpetaActual: string | null }>({
    obras: [],
    carpetaActual: null,
  });
  const [estado, setEstado] = useState<ObrasCargadas["estado"]>("cargando");

  useEffect(() => {
    if (!puedeLeer) return;
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
  }, [intento, alExpirar, puedeLeer]);

  const recargar = useCallback(() => {
    setEstado("cargando");
    setIntento((n) => n + 1);
  }, []);
  return { obras: datos.obras, carpetaActual: datos.carpetaActual, estado: puedeLeer ? estado : "sin_permiso", recargar };
}
