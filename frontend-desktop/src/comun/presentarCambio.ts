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
// tabla que nombra el prefijo de la clave del cambio (`esp_tramos:...`), y de una posterior a la anterior. Como un texto
// libre puede llevar él mismo «; <columna>=» (un nombre «Toma; x=3»), no gana la primera coincidencia de cada columna: de
// todas las lecturas posibles se elige la que reconoce más columnas y, si dos reconocen las mismas, la que toma más tarde la
// coincidencia de una columna, que deja entero el texto libre que va antes (resto N1 del árbitro de la tanda, F8).
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

interface Marca {
  columna: string;
  // El lugar de la columna en su tabla: una lectura válida los recorre en orden creciente.
  orden: number;
  desde: number;
  valorDesde: number;
}

// La cadena de marcas más larga que empieza en la primera (la que abre el resumen) y sube por el orden de las columnas.
// `largo[i]` es la más larga que acaba en la marca i (0: ninguna llega a ella) y `previa[i]`, la marca anterior en esa cadena.
// Con `>=` gana, en un empate, la marca anterior más tardía y, al final, la cadena que acaba más tarde.
function mejorLectura(candidatas: readonly Marca[]): Marca[] {
  const largo = candidatas.map((_, i): number => (i === 0 ? 1 : 0));
  const previa = candidatas.map(() => -1);
  for (let i = 1; i < candidatas.length; i++) {
    for (let j = 0; j < i; j++) {
      if (largo[j]! > 0 && candidatas[j]!.orden < candidatas[i]!.orden && largo[j]! + 1 >= largo[i]!) {
        largo[i] = largo[j]! + 1;
        previa[i] = j;
      }
    }
  }
  let fin = 0;
  largo.forEach((l, i) => {
    if (l >= largo[fin]!) fin = i;
  });
  const cadena: Marca[] = [];
  for (let i = fin; i >= 0; i = previa[i]!) cadena.unshift(candidatas[i]!);
  return cadena;
}

function partirResumen(valor: string, columnas: string[]): [string, string][] | null {
  const buscador = new RegExp(`(?:^|; )(${columnas.join("|")})=`, "g");
  const candidatas: Marca[] = [...valor.matchAll(buscador)].map((m) => ({
    columna: m[1]!,
    orden: columnas.indexOf(m[1]!),
    desde: m.index,
    valorDesde: m.index + m[0].length,
  }));
  if (candidatas.length === 0 || candidatas[0]!.desde !== 0) return null;
  const marcas = mejorLectura(candidatas);
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

// Las especificaciones de un renglón («clave=valor; clave=valor», ordenadas: `_cambios_de_especificaciones` de
// aplicacion/hoja.py). Una clave que empieza por «_» es una directiva de Sílice, no un dato de la persona: la del frente
// (`aplicacion/frentes.py`, «_frente») sale como «Frente: …» y las que no tienen rótulo no se muestran (ronda 1 del
// árbitro de la ola 2, hallazgo 6). Un valor puede llevar «; » (un frente «Estación; 2»): solo se corta antes de otra
// «clave=».
const DIRECTIVAS: Record<string, string> = { _frente: "Frente" };

function especificacionesLegibles(valor: string): string {
  if (valor === "") return "";
  return valor
    .split(/; (?=[^\s;=]+=)/)
    .flatMap((par) => {
      const igual = par.indexOf("=");
      const [k, v] = igual < 0 ? [par, ""] : [par.slice(0, igual), par.slice(igual + 1)];
      if (Object.hasOwn(DIRECTIVAS, k)) return [`${DIRECTIVAS[k]}: ${v}`];
      if (k.startsWith("_")) return [];
      return [igual < 0 ? par : `${k}=${cifraSiLoEs(v)}`];
    })
    .join("; ");
}

// El antes o el después de un cambio de ese campo; `clave` es la de la fila del registro (dice de qué tabla es un resumen).
export function presentarValor(campo: string, valor: string, clave = ""): string {
  if (campo === "especificaciones") return especificacionesLegibles(valor);
  if (campo === "fila") {
    const compuesto = resumenCompuesto(valor, clave);
    if (compuesto !== null) return compuesto;
  }
  if (campo === "vertices") return verticesLegibles(valor);
  return valorDeCambio(campo, valor);
}
