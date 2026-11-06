// Autocompletado de la descripcion de los insumos al componer un APU (AC1, pedido de Eugenio del 2026-10-21; AC1b): de
// que tabla de consulta sale cada tabla de insumos y que columnas se llenan al elegir una sugerencia. Aqui no se calcula
// nada: los montos llegan de la API como decimal con punto y solo se reescriben con la coma de la pagina.
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import type { SugerenciaDeConsulta, TablaDeConsulta } from "../../comun/consulta";
import type { Fila, TipoTabla } from "./tablas";

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

// Lo que el catalogo llena en una fila ademas de la descripcion, y que el catalogo de OTRO insumo no debe mezclar (diseno del
// 2026-10-21, §1.6: «nunca se mezclan en una misma fila»): la unidad (solo materiales) y el precio o el jornal.
export function columnasDelCatalogo(tipo: TipoTabla): string[] {
  return tipo === "materiales" ? ["unidad", COLUMNA_DEL_PRECIO[tipo]] : [COLUMNA_DEL_PRECIO[tipo]];
}

// Los valores que puso el catalogo en una fila y siguen siendo suyos, por columna. Una celda en la que la persona escribio
// sale de aqui y deja de ser del catalogo para siempre.
export type Llenado = Record<string, string>;

export interface Conflicto {
  // El valor del catalogo tal como se lee (formateado) y la frase que lo dice.
  valor: string;
  aviso: string;
}

export interface Eleccion {
  // Las celdas a escribir; un texto vacio vacia la celda (era del catalogo y el insumo nuevo no trae ese dato).
  valores: Record<string, string>;
  // Lo que el catalogo es dueno ahora en la fila (para la proxima eleccion).
  llenado: Llenado;
  // Por columna: lo que el catalogo tiene y NO se escribio porque la persona ya habia puesto otra cosa en esa celda.
  conflictos: Record<string, Conflicto>;
  // Por que el precio quedo vacio (otra moneda), solo si la celda del precio quedo vacia.
  aviso: string | null;
}

// Elegir un insumo en una fila que ya tiene cosas (dictamen del autocompletado, BLOQUEANTE). Por cada celda que el catalogo
// llena: si esta vacia o todavia tiene lo que puso el catalogo, se reemplaza con lo del insumo nuevo, o se vacia si el nuevo
// no trae ese dato (nunca queda el 18,00 del insumo anterior); si la persona escribio otra cosa, no se pisa y se dice lo que
// el catalogo tiene. La interfaz no calcula: solo compara textos y reescribe el decimal que mando la API.
export function aplicarEleccion(
  tipo: TipoTabla,
  sugerencia: SugerenciaDeConsulta,
  monedaDeTrabajo: string | null,
  fila: Fila,
  llenadoPrevio: Llenado,
): Eleccion {
  const trae = valoresAlElegir(tipo, sugerencia, monedaDeTrabajo);
  const valores: Record<string, string> = { descripcion: trae.valores.descripcion };
  const llenado: Llenado = {};
  const conflictos: Record<string, Conflicto> = {};
  const columnaDelPrecio = COLUMNA_DEL_PRECIO[tipo];
  for (const columna of columnasDelCatalogo(tipo)) {
    const actual = fila[columna] ?? "";
    const previo = llenadoPrevio[columna];
    const esDelCatalogo = previo !== undefined && actual === previo;
    const conserva = actual.trim() === "" || esDelCatalogo;
    const nuevo = trae.valores[columna];
    if (nuevo !== undefined) {
      if (conserva) {
        valores[columna] = nuevo;
        llenado[columna] = nuevo;
      } else if (actual !== nuevo) {
        // El valor del precio solo llega con su moneda (`valoresAlElegir`).
        const frase =
          columna === "unidad"
            ? `El catálogo tiene la unidad «${nuevo}»; se conserva la que escribió.`
            : `El catálogo tiene ${nuevo} ${sugerencia.moneda}; se conserva ${columna === "sueldo" ? "el sueldo" : "el precio"} que escribió.`;
        conflictos[columna] = { valor: nuevo, aviso: frase };
      }
    } else if (esDelCatalogo) {
      valores[columna] = ""; // el insumo anterior ya no esta y el nuevo no trae ese dato
    }
  }
  const precioFinal = valores[columnaDelPrecio] ?? fila[columnaDelPrecio] ?? "";
  return { valores, llenado, conflictos, aviso: precioFinal.trim() === "" ? trae.aviso : null };
}
