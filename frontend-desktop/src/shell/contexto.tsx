import { createContext, useContext } from "react";
import type { CasoRespuesta, SesionRespuesta } from "../api/tipos";

// Lo que toda pagina necesita saber de la aplicacion. Vive en memoria (nada en localStorage, RT-9).
export interface Aplicacion {
  sesion: SesionRespuesta;
  // Codigo del proyecto elegido en la cabecera, o null si no hay ninguno.
  proyecto: string | null;
  // Caso (base de datos) en uso, o null mientras carga o si la API no lo informa.
  caso: CasoRespuesta | null;
  // Para volver a pedir la lista de proyectos (por ejemplo, despues de crear uno).
  recargarProyectos: () => void;
  // La API contesto 401: la sesion vencio.
  alExpirar: () => void;
}

export const ContextoAplicacion = createContext<Aplicacion | null>(null);

export function useAplicacion(): Aplicacion {
  const valor = useContext(ContextoAplicacion);
  if (!valor) throw new Error("useAplicacion se usa dentro del Shell.");
  return valor;
}
