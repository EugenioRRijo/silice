import { ErrorDeApi } from "../../api/cliente";

export const SIN_PERMISO = "Su cuenta no tiene permiso para esta acción";

export interface Reacciones {
  // La API contesto 401: la sesion vencio.
  alExpirar: () => void;
  // La API contesto 403: la cuenta no puede operar la arenera.
  alDenegar: () => void;
}

// Que hacer con el error de una accion de la persona (registrar, importar, resolver): si es de sesion o de permiso se
// avisa a la pagina y no se muestra aqui; el resto se devuelve para mostrarlo con su `detalle` (o el mensaje fijo).
export function reaccionar(error: unknown, { alExpirar, alDenegar }: Reacciones): unknown {
  if (error instanceof ErrorDeApi && error.estado === 401) {
    alExpirar();
    return null;
  }
  if (error instanceof ErrorDeApi && error.estado === 403) {
    alDenegar();
    return null;
  }
  return error;
}
