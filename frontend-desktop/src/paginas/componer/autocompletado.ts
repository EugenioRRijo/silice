// Autocompletado de la descripcion de los insumos al componer un APU (AC1, pedido de Eugenio del 2026-10-21; AC1b): de
// que tabla de consulta sale cada tabla de insumos y que columnas se llenan al elegir una sugerencia. Aqui no se calcula
// nada: los montos llegan de la API como decimal con punto y solo se reescriben con la coma de la pagina.
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import type { SugerenciaDeConsulta, TablaDeConsulta } from "../../comun/consulta";
import type { TipoTabla } from "./tablas";

// `GET /v1/consulta/insumos` junta materiales y equipos del catalogo (aplicacion/consulta.py, TIPOS_DE_INSUMO): no hay una
// tabla solo de equipos, asi que las dos tablas piden «insumos» y la fuente de cada sugerencia dice si es material o
// equipo. La mano de obra sale de «salarios_cct»: los oficios del catalogo con su jornal.
export const TABLA_DE_CONSULTA: Record<TipoTabla, TablaDeConsulta> = {
  materiales: "insumos",
  equipos: "insumos",
  mano_obra: "salarios_cct",
};

// La columna de la tabla que recibe el precio: el precio de un material o un equipo, el jornal (sueldo) de la mano de
// obra. Un material ademas recibe la unidad; las otras dos tablas no tienen esa columna.
export const COLUMNA_DEL_PRECIO: Record<TipoTabla, "precio" | "sueldo"> = {
  materiales: "precio",
  equipos: "precio",
  mano_obra: "sueldo",
};

export interface AlElegir {
  // Las celdas que se llenan.
  valores: Record<string, string>;
  // Por que el precio no se lleno aunque la lista lo tiene (otra moneda), en texto llano; null si no hay nada que decir.
  aviso: string | null;
}

// Las celdas que se llenan al elegir una sugerencia: siempre la descripcion (y la unidad, si es un material y la trae) y el
// precio solo si viene de la lista para armar en la moneda de la carpeta. El servidor ya no lo manda en otra moneda
// (aplicacion/consulta.py); si aun asi llegara en otra, o sin moneda, no se copia. Sin la moneda de la carpeta (la API
// no la dio) manda la comparacion del servidor. Lo que no viene no se llena (no se inventa ni se borra lo que hay).
export function valoresAlElegir(
  tipo: TipoTabla,
  sugerencia: SugerenciaDeConsulta,
  monedaDeTrabajo: string | null,
): AlElegir {
  const columna = COLUMNA_DEL_PRECIO[tipo];
  const valores: Record<string, string> = { descripcion: sugerencia.descripcion || sugerencia.etiqueta };
  if (tipo === "materiales" && sugerencia.unidad) valores.unidad = sugerencia.unidad;
  const { precio, moneda } = sugerencia;
  if (!precio) return { valores, aviso: sugerencia.aviso_precio || null };
  if (!moneda) return { valores, aviso: null };
  if (monedaDeTrabajo !== null && moneda !== monedaDeTrabajo) {
    return { valores, aviso: `El catálogo lo tiene en ${moneda}; escriba el ${columna} en ${monedaDeTrabajo}.` };
  }
  valores[columna] = formatoEsVe(precio);
  return { valores, aviso: null };
}
