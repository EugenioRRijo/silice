// El presentador único de las filas del registro de cambios: lo comparten «Guardar versión», Versiones y Revisar › «Quién
// cambió qué». El servidor guarda claves técnicas («parametro», «control|spi_error», «largo=4.5; ancho=3.2»): forman parte
// de la huella y no se tocan; aquí solo se presentan en español llano, con coma decimal y punto de miles.

import { cifraSiLoEs } from "../indicadores/formatoEsVe";
import { rotuloDeOrigen } from "./rotuloDeOrigen";
import { rotuloDeParametro, valorDeCambio } from "./rotulos";
import { ROTULOS_DE_COLUMNA } from "./rotulosDeColumna";

// La clave de la fila del registro: un parámetro tiene su rótulo; lo demás es un renglón o una fila del metraje.
export function presentarClave(objeto: string, clave: string): string {
  return objeto === "parametro" ? rotuloDeParametro(clave) : rotuloDeOrigen(clave);
}

// El alta o la baja de una fila de metraje lleva el resumen «clave=valor; clave=valor» (`_resumen_de_fila`,
// aplicacion/hoja.py): las columnas de su tabla, en orden y sin las vacías. Pero un valor puede llevar «; » (los vértices
// «1.5,0,2.5; 1.5,0,0.6», un nombre libre, las especificaciones): solo se corta en «; » seguido de una columna de la
// tabla que nombra el prefijo de la clave del cambio (`esp_tramos:...`), y de una posterior a la anterior.
const PREFIJO_DE_TABLA: Record<string, string> = {
  esp_origenes: "origenes",
  esp_ambientes: "ambientes",
  esp_fuentes: "fuentes",
  esp_puntos: "puntos",
  esp_tramos: "tramos",
};

function tablaDeLaClave(clave: string): Record<string, string> | null {
  const prefijo = clave.split(":")[0] ?? "";
  const tabla = PREFIJO_DE_TABLA[prefijo];
  return tabla === undefined ? null : (ROTULOS_DE_COLUMNA[tabla] ?? null);
}

function partirResumen(valor: string, columnas: string[]): [string, string][] | null {
  const marcas: { columna: string; desde: number; valorDesde: number }[] = [];
  let ultima = -1;
  const buscador = new RegExp(`(?:^|; )(${columnas.join("|")})=`, "g");
  for (const m of valor.matchAll(buscador)) {
    const posicion = columnas.indexOf(m[1]!);
    if (posicion <= ultima) continue;
    ultima = posicion;
    marcas.push({ columna: m[1]!, desde: m.index!, valorDesde: m.index! + m[0].length });
  }
  if (marcas.length === 0 || marcas[0]!.desde !== 0) return null;
  return marcas.map((marca, i) => {
    const fin = i + 1 < marcas.length ? marcas[i + 1]!.desde : valor.length;
    return [marca.columna, valor.slice(marca.valorDesde, fin)];
  });
}

// Los vértices «x,y,z; x,y,z» (puntos decimales del servidor) como «(x; y; z), (x; y; z)» con coma decimal.
function verticesLegibles(texto: string): string {
  return texto
    .split("; ")
    .map((v) => `(${v.split(",").map(cifraSiLoEs).join("; ")})`)
    .join(", ");
}

function resumenCompuesto(valor: string, clave: string): string | null {
  const rotulos = tablaDeLaClave(clave);
  if (rotulos === null) return null;
  const pares = partirResumen(valor, Object.keys(rotulos));
  if (pares === null) return null;
  return pares
    .map(([k, v]) => `${rotulos[k]}=${k === "vertices" ? verticesLegibles(v) : cifraSiLoEs(v)}`)
    .join("; ");
}

// El antes o el después de un cambio de ese campo; `clave` es la de la fila del registro (dice de qué tabla es un resumen).
export function presentarValor(campo: string, valor: string, clave = ""): string {
  if (campo === "fila") {
    const compuesto = resumenCompuesto(valor, clave);
    if (compuesto !== null) return compuesto;
  }
  if (campo === "vertices") return verticesLegibles(valor);
  return valorDeCambio(campo, valor);
}
