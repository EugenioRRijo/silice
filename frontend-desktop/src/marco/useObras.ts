import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { ErrorDeApi, pedir } from "../api/cliente";
import type { ObraDeCarpetaRespuesta, ObrasTodasRespuesta } from "../api/tipos";

export type ObraDeCarpeta = ObraDeCarpetaRespuesta;

export interface ObrasCargadas {
  obras: ObraDeCarpeta[];
  // La carpeta abierta en la sesión; null si es la de la empresa.
  carpetaActual: string | null;
  // El título de esa carpeta (lo da el servidor, aunque no tenga obras).
  tituloActual: string;
  // «sin_permiso»: la cuenta no lee obras (sin `leer_proyecto`): no se piden y no hay nada que mostrar.
  estado: "cargando" | "lista" | "error" | "sin_permiso";
  recargar: () => void;
}

// Las obras de todas las carpetas a las que la cuenta tiene acceso (`GET /v1/obras/todas`, Tarea 3 del plan del marco):
// con `abrir_carpeta` son las de todas las carpetas; sin él, solo las de la abierta. Solo el marco la pide (una vez por
// carga) y la reparte por `ContextoObras` a la barra lateral y al buscador (prueba en vivo, 2026-11-18: con una lectura
// por cada uno, al abrir otra carpeta la barra seguía con la anterior). Mientras recarga conserva la lista anterior y el
// estado vuelve a «cargando». Sin `leer_proyecto` la API contestaría 403: no se pide (VB-9).
export function useCargaDeObras(acciones: readonly string[], alExpirar: () => void): ObrasCargadas {
  const puedeLeer = acciones.includes("leer_proyecto");
  const [intento, setIntento] = useState(0);
  const [datos, setDatos] = useState<{ obras: ObraDeCarpeta[]; carpetaActual: string | null; tituloActual: string }>({
    obras: [],
    carpetaActual: null,
    tituloActual: "",
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
        setDatos({ obras: r.obras, carpetaActual: r.carpeta_actual ?? null, tituloActual: r.carpeta_actual_titulo ?? "" });
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
  return useMemo(
    () => ({ obras: datos.obras, carpetaActual: datos.carpetaActual, tituloActual: datos.tituloActual, estado: puedeLeer ? estado : "sin_permiso", recargar }),
    [datos, puedeLeer, estado, recargar],
  );
}

export const ContextoObras = createContext<ObrasCargadas | null>(null);

// Lo que leen la barra lateral y el buscador: lo que el marco ya pidió.
export function useObras(): ObrasCargadas {
  const valor = useContext(ContextoObras);
  if (!valor) throw new Error("useObras se usa dentro del marco.");
  return valor;
}
