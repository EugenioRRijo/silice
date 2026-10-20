import { fechaValida, rangoInvertido } from "../historico/porcentaje";
import type { AuditoriaGuardadaRespuesta } from "../inicio/UltimasAuditorias";

// Lo que la API del historial ofrece es una lista de las ultimas auditorias (sin filtros) y el detalle de una. Los
// filtros de la pagina se aplican aqui, sobre texto: la fecha ISO se compara como cadena (AAAA-MM-DD ordena como
// fecha) y los conteos son enteros. No hay montos que calcular.

export type TipoFiltro = "todos" | "libro" | "pdf";
export type ResultadoFiltro = "todos" | "con_errores" | "solo_advertencias" | "limpia";

export interface FiltrosHistorial {
  desde: string;
  hasta: string;
  tipo: TipoFiltro;
  resultado: ResultadoFiltro;
}

export const FILTROS_VACIOS: FiltrosHistorial = { desde: "", hasta: "", tipo: "todos", resultado: "todos" };

export function clasificar(errores: number, advertencias: number): Exclude<ResultadoFiltro, "todos"> {
  if (errores > 0) return "con_errores";
  return advertencias > 0 ? "solo_advertencias" : "limpia";
}

// «2026-10-18T14:32:05» -> «18/10/2026 14:32»; «2026-07-31» -> «31/07/2026». Lo que no sea ISO queda tal cual.
export function fechaEsVe(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}))?/.exec(iso);
  if (!m) return iso;
  const dia = `${m[3]}/${m[2]}/${m[1]}`;
  return m[4] ? `${dia} ${m[4]}:${m[5]}` : dia;
}

// El motivo por el que los filtros de fecha no valen, en palabras de la persona; null si valen.
export function filtrosInvalidos({ desde, hasta }: FiltrosHistorial): string | null {
  if (desde !== "" && !fechaValida(desde)) return "La fecha «Desde» no es válida: use AAAA-MM-DD.";
  if (hasta !== "" && !fechaValida(hasta)) return "La fecha «Hasta» no es válida: use AAAA-MM-DD.";
  if (rangoInvertido(desde, hasta)) return "La fecha «Desde» es posterior a «Hasta».";
  return null;
}

// Una fecha mal escrita o un rango invertido no filtra por fecha: la pagina muestra el aviso de `filtrosInvalidos` y deja la lista como esta.
export function filtrar(
  lista: readonly AuditoriaGuardadaRespuesta[],
  { desde, hasta, tipo, resultado }: FiltrosHistorial,
): AuditoriaGuardadaRespuesta[] {
  const invertido = rangoInvertido(desde, hasta);
  const inicio = fechaValida(desde) && !invertido ? desde : null;
  const fin = fechaValida(hasta) && !invertido ? hasta : null;
  return lista.filter((a) => {
    const dia = a.fecha.slice(0, 10);
    if (inicio !== null && dia < inicio) return false;
    if (fin !== null && dia > fin) return false;
    if (tipo !== "todos" && a.tipo !== tipo) return false;
    return resultado === "todos" || clasificar(a.errores, a.advertencias) === resultado;
  });
}
