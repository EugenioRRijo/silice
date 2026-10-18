// El contrato lleva el valor de cada celda como texto, sin su tipo. Se deduce de la forma del texto: un numero
// decimal, una fecha ISO, TRUE/FALSE o texto. Un codigo con ceros a la izquierda ("007") es texto; un texto "100"
// guardado como cadena se tomaria por numero (limite declarado, RS2.4-3: pedir un campo `tipo` a la API lo cierra).
export type TipoDeValor = "numero" | "fecha" | "booleano" | "texto";

const NUMERO = /^-?(0|[1-9][0-9]*)(\.[0-9]+)?$/;
const FECHA = /^[0-9]{4}-[0-9]{2}-[0-9]{2}(?:[T ].*)?$/;

export function tipoDeValor(valor: string): TipoDeValor {
  if (NUMERO.test(valor)) return "numero";
  if (FECHA.test(valor)) return "fecha";
  if (valor === "TRUE" || valor === "FALSE") return "booleano";
  return "texto";
}
