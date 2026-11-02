import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router";
import { ErrorDeApi, pedir } from "../api/cliente";
import type { PendienteDeObra, PendientesTodasRespuesta } from "../api/tipos";
import { mensajeDeError } from "../comun/errores";
import { RUTA_DE_PENDIENTES } from "./secciones";

export type EstadoPendientes =
  | { estado: "cargando" }
  | { estado: "error"; mensaje: string }
  | { estado: "listo"; pendientes: PendienteDeObra[]; carpetasOmitidas: number };

export type PendientesDelMarco = EstadoPendientes & { recargar: () => void };

const RUTA = "/v1/obras/pendientes/todas";
const CARGANDO: EstadoPendientes = { estado: "cargando" };
const NINGUNO: EstadoPendientes = { estado: "listo", pendientes: [], carpetasOmitidas: 0 };

// Los pendientes de todas las obras (`GET /v1/obras/pendientes/todas`, rediseño F3): el marco los pide una vez y los
// reparte por `ContextoPendientes` a la bandeja y a la barra lateral, que no vuelven a pedirlos.
// - Sin `leer_proyecto` (el administrador) la API contestaría 403: no se piden y no hay ninguno (sin error). Un 403 que
//   llegue igual se lee del mismo modo.
// - Cada vez que se entra en `#/pendientes` se vuelven a pedir (foco 4: lo resuelto en la obra no se queda). Una lectura
//   que empezó antes de entrar (en otra ruta, o antes de la redirección de `#/`) se descarta y se vuelve a pedir, para
//   que nunca queden datos de antes de entrar; solo no se repite la que ya empezó estando en Pendientes (la navegación
//   puede cambiar la `key` dos veces seguidas).
// - Un 401 da la sesión por vencida.
export function useCargaDePendientes(acciones: readonly string[], alExpirar: () => void): PendientesDelMarco {
  const puedeLeer = acciones.includes("leer_proyecto");
  const { pathname, key } = useLocation();
  const [intento, setIntento] = useState(0);
  const [estado, setEstado] = useState<EstadoPendientes>(CARGANDO);
  const [entrada, setEntrada] = useState(key);
  // La lectura en curso empezó estando en Pendientes (entonces no hace falta repetirla al entrar). Una que empieza en
  // «/» cuenta como tal: esa ruta redirige a Pendientes y repetirla pediría dos veces una lectura cara.
  const [leyendoEnPendientes, setLeyendoEnPendientes] = useState(pathname === RUTA_DE_PENDIENTES || pathname === "/");
  // Al salir a otra ruta esa lectura ya no cuenta: al volver se pide de nuevo (lo resuelto fuera no se queda).
  if (leyendoEnPendientes && pathname !== RUTA_DE_PENDIENTES && pathname !== "/") setLeyendoEnPendientes(false);
  // Se ajusta durante el dibujo (sin efecto), como el aviso del marco.
  if (pathname === RUTA_DE_PENDIENTES && key !== entrada) {
    setEntrada(key);
    if (estado.estado !== "cargando" || !leyendoEnPendientes) {
      setEstado(CARGANDO);
      setIntento((n) => n + 1);
      setLeyendoEnPendientes(true);
    }
  }

  useEffect(() => {
    if (!puedeLeer) return;
    let vigente = true;
    pedir<PendientesTodasRespuesta>(RUTA)
      .then((r) => {
        if (!vigente) return;
        if (!Array.isArray(r?.pendientes)) setEstado({ estado: "error", mensaje: mensajeDeError(null) });
        else setEstado({ estado: "listo", pendientes: r.pendientes, carpetasOmitidas: r.carpetas_omitidas ?? 0 });
      })
      .catch((e: unknown) => {
        if (!vigente) return;
        if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
        else if (e instanceof ErrorDeApi && e.estado === 403) setEstado(NINGUNO);
        else setEstado({ estado: "error", mensaje: mensajeDeError(e) });
      });
    return () => {
      vigente = false;
    };
  }, [intento, puedeLeer, alExpirar]);

  const recargar = useCallback(() => {
    setEstado(CARGANDO);
    setIntento((n) => n + 1);
  }, []);
  return useMemo(() => ({ ...(puedeLeer ? estado : NINGUNO), recargar }), [puedeLeer, estado, recargar]);
}

export const ContextoPendientes = createContext<PendientesDelMarco | null>(null);

// Lo que leen la bandeja y la barra lateral: lo que el marco ya pidió.
export function usePendientes(): PendientesDelMarco {
  const valor = useContext(ContextoPendientes);
  if (!valor) throw new Error("usePendientes se usa dentro del marco.");
  return valor;
}
