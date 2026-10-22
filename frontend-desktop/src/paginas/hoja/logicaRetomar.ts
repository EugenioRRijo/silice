// Lógica pura de retomar un borrador (rebanada 3c-3: E10 y E11 del diseño §4.4, 3c-F16). El borrador vive en el servidor:
// al volver a la página o recargar, la persona puede seguir donde iba.
import { ErrorDeApi } from "../../api/cliente";

export const RUTA_DE_BORRADORES = "/v1/hoja/borradores";

export interface OfertaDeRetomar {
  id: string;
  proyecto: string;
  // null: el borrador de un proyecto que todavía no tiene versiones.
  version: string | null;
  cambios: number;
  tocado: string;
}

function esOferta(x: unknown): x is OfertaDeRetomar {
  if (x === null || typeof x !== "object") return false;
  const o = x as Record<string, unknown>;
  return (
    typeof o["id"] === "string" &&
    typeof o["proyecto"] === "string" &&
    (typeof o["version"] === "string" || o["version"] === null) &&
    typeof o["cambios"] === "number"
  );
}

// Los borradores de esta ficha que son del proyecto abierto y tienen cambios sin guardar. Si la respuesta no es una lista no se
// ofrece nada: abrir la hoja no puede depender de esta lectura. El servidor llama `proyecto` al NOMBRE del proyecto y la
// cabecera trae su CÓDIGO: vale cualquiera de los dos.
export function ofertasDeRetomar(respuesta: unknown, proyecto: string, nombre: string | null = null): OfertaDeRetomar[] {
  const lista =
    Array.isArray(respuesta) ? respuesta : respuesta !== null && typeof respuesta === "object" ? (respuesta as Record<string, unknown>)["borradores"] : null;
  if (!Array.isArray(lista)) return [];
  return lista.filter(esOferta).filter((o) => (o.proyecto === proyecto || o.proyecto === nombre) && o.cambios > 0);
}

// «Retomar borrador de OF-001 (2 cambios)»; con varios del proyecto, cada uno dice su versión.
export function rotuloDeOferta(oferta: OfertaDeRetomar, proyecto: string, variasDelProyecto: boolean): string {
  const donde = variasDelProyecto ? (oferta.version === null ? ", en blanco" : `, versión ${oferta.version}`) : "";
  const cambios = oferta.cambios === 1 ? "1 cambio" : `${oferta.cambios} cambios`;
  return `Retomar borrador de ${proyecto}${donde} (${cambios})`;
}

// E11: abrir una versión que ya tiene un borrador con cambios responde 409 con `borrador_id`.
export function borradorExistente(error: unknown): string | null {
  if (!(error instanceof ErrorDeApi) || error.estado !== 409) return null;
  const cuerpo = error.cuerpo;
  if (cuerpo === null || typeof cuerpo !== "object") return null;
  const id = (cuerpo as Record<string, unknown>)["borrador_id"];
  return typeof id === "string" && id !== "" ? id : null;
}
