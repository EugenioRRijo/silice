// Autocompletado de la descripcion de los insumos al componer un APU (AC1, pedido de Eugenio del 2026-10-21): de que
// tabla de consulta sale cada tabla de insumos y que columnas se llenan al elegir una sugerencia. Aqui no se calcula
// nada: los montos llegan de la API como decimal con punto y solo se reescriben con la coma de la pagina.
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import type { TablaDeConsulta } from "../../comun/consulta";
import type { InsumoCatalogo } from "./cliente";
import type { TipoTabla } from "./tablas";

// `GET /v1/consulta/insumos` junta materiales y equipos del catalogo (aplicacion/consulta.py, TIPOS_DE_INSUMO): no hay una
// tabla solo de equipos, asi que las dos tablas piden «insumos» y la fuente de cada sugerencia dice si es material o
// equipo. La mano de obra sale de «salarios_cct»: los oficios del catalogo con su jornal.
export const TABLA_DE_CONSULTA: Record<TipoTabla, TablaDeConsulta> = {
  materiales: "insumos",
  equipos: "insumos",
  mano_obra: "salarios_cct",
};

// La columna de la tabla que recibe el precio del catalogo: el precio de un material o un equipo, el jornal (sueldo) de la
// mano de obra. Un material ademas recibe la unidad; las otras dos tablas no tienen esa columna.
const COLUMNA_DEL_PRECIO: Record<TipoTabla, string> = {
  materiales: "precio",
  equipos: "precio",
  mano_obra: "sueldo",
};

// La etiqueta de una sugerencia es «Descripcion (CODIGO, unidad)»: si el catalogo completo no se pudo leer, la descripcion
// se saca de ahi quitando solo ese cierre, el del codigo del insumo. Cualquier otra cosa queda tal cual.
export function descripcionDeEtiqueta(etiqueta: string, codigo: string): string {
  const cierre = ` (${codigo}`;
  const inicio = etiqueta.lastIndexOf(cierre);
  const resto = inicio > 0 ? etiqueta.slice(inicio + cierre.length) : "";
  if (inicio > 0 && (resto === ")" || (resto.startsWith(", ") && resto.endsWith(")")))) {
    return etiqueta.slice(0, inicio);
  }
  return etiqueta;
}

// Las celdas que se llenan al elegir una sugerencia: la descripcion y, si el catalogo las trae, la unidad y el precio.
// Lo que no viene no se llena (no se inventa ni se borra lo que la persona ya puso).
export function valoresAlElegir(
  tipo: TipoTabla,
  insumo: InsumoCatalogo | null,
  etiqueta: string,
  codigo: string,
): Record<string, string> {
  if (insumo === null) return { descripcion: descripcionDeEtiqueta(etiqueta, codigo) };
  const valores: Record<string, string> = { descripcion: insumo.descripcion };
  if (tipo === "materiales" && insumo.unidad) valores.unidad = insumo.unidad;
  if (insumo.precio_vigente) valores[COLUMNA_DEL_PRECIO[tipo]] = formatoEsVe(insumo.precio_vigente);
  return valores;
}
