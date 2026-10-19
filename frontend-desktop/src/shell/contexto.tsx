import { createContext, useContext } from "react";
import type { CasoRespuesta, SesionRespuesta } from "../api/tipos";
import type { AlmacenDelVisor } from "../visor/almacen";
import type { CrearHojaVisor } from "../visor/hojaVisor";

// Lo que toda pagina necesita saber de la aplicacion. Vive en memoria (nada en localStorage, RT-9).
export interface Aplicacion {
  sesion: SesionRespuesta;
  // Codigo del proyecto elegido en la cabecera, o null si no hay ninguno.
  proyecto: string | null;
  // Nombre del proyecto elegido (el selector guarda el codigo); null si no hay o aun no carga la lista.
  nombreProyecto?: string | null;
  // Caso (base de datos) en uso, o null mientras carga o si la API no lo informa.
  caso: CasoRespuesta | null;
  // Para volver a pedir la lista de proyectos (por ejemplo, despues de crear uno).
  recargarProyectos: () => void;
  // La API contesto 401: la sesion vencio.
  alExpirar: () => void;
  // «Libro de la empresa»: lo abierto vive por encima de la puerta de sesion (UC-26), asi que el almacen llega de
  // App; la ranura es el punto de montaje de la cabecera donde la pagina pinta la fecha de devolucion, el nombre
  // del libro y Cambiar libro (null mientras la cabecera no la ha creado); `crearHojaVisor` solo cambia en pruebas.
  almacenDelLibro?: AlmacenDelVisor;
  ranuraCabecera?: HTMLElement | null;
  crearHojaVisor?: CrearHojaVisor;
}

export const ContextoAplicacion = createContext<Aplicacion | null>(null);

export function useAplicacion(): Aplicacion {
  const valor = useContext(ContextoAplicacion);
  if (!valor) throw new Error("useAplicacion se usa dentro del Shell.");
  return valor;
}
