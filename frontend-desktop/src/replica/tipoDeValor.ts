// El contrato lleva el valor de cada celda como texto, sin su tipo. Se deduce de la forma del texto: un numero
// decimal, una fecha ISO, TRUE/FALSE o texto. Un codigo con ceros a la izquierda ("007") es texto; un texto "100"
// guardado como cadena se tomaria por numero (limite declarado, RS2.4-3: pedir un campo `tipo` a la API lo cierra).
export type TipoDeValor = "numero" | "fecha" | "booleano" | "texto";

const NUMERO = /^-?(0|[1-9][0-9]*)(\.[0-9]+)?$/;
// Notacion cientifica (1.5e-07, 1e+16): con signo en el exponente o con decimales. "1e5" sigue siendo texto: asi no
// se confunde con un codigo.
const CIENTIFICO = /^-?(0|[1-9][0-9]*)(?:\.([0-9]+)[eE][+-]?[0-9]+|[eE][+-][0-9]+)$/;
const FECHA = /^[0-9]{4}-[0-9]{2}-[0-9]{2}(?:[T ].*)?$/;

export function tipoDeValor(valor: string): TipoDeValor {
  if (NUMERO.test(valor) || CIENTIFICO.test(valor)) return "numero";
  if (FECHA.test(valor)) return "fecha";
  if (valor === "TRUE" || valor === "FALSE") return "booleano";
  return "texto";
}

// Si el texto esta en notacion cientifica, el patron de Excel que la muestra con los mismos decimales de la mantisa
// ("1.5e-07" -> "0.0E+00"); null si no lo esta.
export function patronCientifico(valor: string): string | null {
  const m = CIENTIFICO.exec(valor);
  if (!m) return null;
  const decimales = m[2]?.length ?? 0;
  return `0${decimales > 0 ? `.${"0".repeat(decimales)}` : ""}E+00`;
}
