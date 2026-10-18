import { ErrorDeApi } from "../api/cliente";

export const MENSAJE_INESPERADO = "Ocurrió un error inesperado. Inténtelo de nuevo.";

// El texto que se le muestra a la persona: el `detalle` de la API tal cual (con la espera si es un 429), un texto
// ya escrito, o el mensaje general. Nunca el `message` de un Error cualquiera: puede traer rutas o detalles internos.
export function mensajeDeError(error: unknown): string {
  if (error instanceof ErrorDeApi) {
    const espera = error.reintentarEnSegundos;
    if (error.estado === 429 && espera !== null) {
      const unidad = espera === 1 ? "segundo" : "segundos";
      return `${error.detalle} Espere ${espera} ${unidad} antes de volver a intentarlo.`;
    }
    return error.detalle;
  }
  if (typeof error === "string" && error) return error;
  return MENSAJE_INESPERADO;
}
