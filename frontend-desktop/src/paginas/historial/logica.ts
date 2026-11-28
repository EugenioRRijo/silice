import { fechaValida, rangoInvertido } from "../../comun/porcentaje";
import { extraerPersona } from "../../comun/responsable";
import { fechaEsVe } from "../../indicadores/formatoEsVe";
import type { AuditoriaGuardadaRespuesta } from "../inicio/UltimasAuditorias";

// Lo que la API del historial ofrece es una lista de las ultimas auditorias (sin filtros) y el detalle de una. Los
// filtros de la pagina se aplican aqui, sobre texto: la fecha ISO se compara como cadena (AAAA-MM-DD ordena como
// fecha) y los conteos son enteros. No hay montos que calcular.

export interface AuditoriaEnHistorial extends AuditoriaGuardadaRespuesta {
  // Opcional mientras la lista `/v1/auditorias-libro` no envíe quién auditó.
  usuario?: string | null;
  responsable?: string | null;
}

export type TipoFiltro = "todos" | "libro" | "pdf";
export type ResultadoFiltro = "todos" | "con_errores" | "solo_advertencias" | "limpia";

export interface FiltrosHistorial {
  desde: string;
  hasta: string;
  tipo: TipoFiltro;
  resultado: ResultadoFiltro;
  persona: string;
}

export const FILTROS_VACIOS: FiltrosHistorial = { desde: "", hasta: "", tipo: "todos", resultado: "todos", persona: "" };


export interface OpcionDePersona {
  clave: string;
  nombre: string;
  etiqueta: string;
}

export { extraerPersona, type PersonaExtraida } from "../../comun/responsable";
import type { PersonaExtraida } from "../../comun/responsable";

export function personaDeAuditoria(a: Pick<AuditoriaEnHistorial, "usuario" | "responsable">): PersonaExtraida | null {
  if (a.responsable !== undefined && a.responsable !== null) {
    return extraerPersona(a.responsable, a.usuario);
  }
  return extraerPersona(a.usuario);
}

export function listarPersonasDeAuditorias(
  lista: readonly Pick<AuditoriaEnHistorial, "usuario" | "responsable">[],
): OpcionDePersona[] {
  const porClave = new Map<string, PersonaExtraida>();
  for (const a of lista) {
    const p = personaDeAuditoria(a);
    if (p !== null && !porClave.has(p.clave)) porClave.set(p.clave, p);
  }
  const unicas = [...porClave.values()].sort((a, b) => a.nombre.localeCompare(b.nombre, "es"));
  const conteos = new Map<string, number>();
  for (const p of unicas) conteos.set(p.nombre, (conteos.get(p.nombre) ?? 0) + 1);
  return unicas.map((p) => ({
    clave: p.clave,
    nombre: p.nombre,
    etiqueta: (conteos.get(p.nombre) ?? 0) > 1 && p.usuario !== null ? `${p.nombre} (${p.usuario})` : p.nombre,
  }));
}

export function clasificar(errores: number, advertencias: number): Exclude<ResultadoFiltro, "todos"> {
  if (errores > 0) return "con_errores";
  return advertencias > 0 ? "solo_advertencias" : "limpia";
}

// «2026-10-18T14:32:05» -> «18/10/2026 14:32»; «2026-07-31» -> «31/07/2026». Vive en formatoEsVe (VB-19).
export { fechaEsVe } from "../../indicadores/formatoEsVe";

// El motivo por el que los filtros de fecha no valen, en palabras de la persona; null si valen.
export function filtrosInvalidos({ desde, hasta }: FiltrosHistorial): string | null {
  if (desde !== "" && !fechaValida(desde)) return "La fecha «Desde» no es válida: use AAAA-MM-DD.";
  if (hasta !== "" && !fechaValida(hasta)) return "La fecha «Hasta» no es válida: use AAAA-MM-DD.";
  if (rangoInvertido(desde, hasta)) return "La fecha «Desde» es posterior a «Hasta».";
  return null;
}

const ETIQUETAS_RESULTADO: Record<Exclude<ResultadoFiltro, "todos">, string> = {
  con_errores: "Con errores",
  solo_advertencias: "Solo advertencias",
  limpia: "Sin errores ni advertencias",
};

export function textoDeFiltrosActivos(filtros: FiltrosHistorial, personas: readonly OpcionDePersona[]): string[] {
  const activos: string[] = [];
  if (filtros.desde !== "") activos.push(`Desde: ${fechaEsVe(filtros.desde)}`);
  if (filtros.hasta !== "") activos.push(`Hasta: ${fechaEsVe(filtros.hasta)}`);
  if (filtros.tipo !== "todos") activos.push(`Tipo: ${filtros.tipo === "pdf" ? "PDF" : "Libro"}`);
  if (filtros.resultado !== "todos") activos.push(`Resultado: ${ETIQUETAS_RESULTADO[filtros.resultado]}`);
  if (filtros.persona !== "") {
    const nombre = personas.find((p) => p.clave === filtros.persona)?.etiqueta ?? filtros.persona;
    activos.push(`Por persona: ${nombre}`);
  }
  return activos;
}

// Una fecha mal escrita o un rango invertido no filtra por fecha: la pagina muestra el aviso de `filtrosInvalidos` y deja la lista como esta.
export function filtrar(
  lista: readonly AuditoriaEnHistorial[],
  { desde, hasta, tipo, resultado, persona }: FiltrosHistorial,
): AuditoriaEnHistorial[] {
  const invertido = rangoInvertido(desde, hasta);
  const inicio = fechaValida(desde) && !invertido ? desde : null;
  const fin = fechaValida(hasta) && !invertido ? hasta : null;
  return lista.filter((a) => {
    const dia = a.fecha.slice(0, 10);
    if (inicio !== null && dia < inicio) return false;
    if (fin !== null && dia > fin) return false;
    if (tipo !== "todos" && a.tipo !== tipo) return false;
    if (resultado !== "todos" && clasificar(a.errores, a.advertencias) !== resultado) return false;
    return persona === "" || personaDeAuditoria(a)?.clave === persona;
  });
}
