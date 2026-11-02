// Las cifras que teclea la persona: coma para los decimales, punto para los miles (regla de Eugenio, 2026-10-25).
//
// Es la misma regla que `aplicacion/cifras.py`, para las pantallas cuyo contrato de API ya es un decimal con punto:
// la pantalla lee lo escrito aqui, antes de enviar, y manda el decimal con punto. Componer y la Hoja no la usan para
// enviar: mandan el texto tal cual y lo interpreta `aplicacion/cifras.py` al recibir. Las dos implementaciones
// cumplen la misma tabla de oraculos escrita a mano (tests/fixtures/cifras_escritas.json).
//
// Se acepta: un menos opcional pegado a la cifra; la parte entera sin separadores («1234») o agrupada de tres en tres
// con punto, sin cero a la izquierda del primer grupo («1.234»); una parte decimal opcional tras una coma («2,5»).
// Todo lo demas se rechaza sin adivinar («2.5», «1,234.5», «1.2345», «0.123», «1 234», «1e3», NaN...). Solo texto:
// nunca pasa por Number, asi una cifra de 40 digitos no pierde ninguno. El cero negativo se lee como cero.
import { DECIMAL, formatoEsVe } from "./formatoEsVe";

export const MENSAJE_CIFRA = "Use la coma para los decimales: por ejemplo 2,5. El punto separa los miles: 1.234,56.";
export const MENSAJE_CIFRA_VACIA = `Escriba un número. ${MENSAJE_CIFRA}`;
export const AYUDA_CIFRAS = "Escriba los decimales con coma: 2,5; el punto separa los miles: 1.234,56.";

// Lo que se recorta en los bordes, y nada mas: el mismo conjunto que `aplicacion/cifras.py` (BLANCOS). `trim()` no
// sirve: recorta otro conjunto (no quita NEL, si quita U+2028 y U+3000).
export const BLANCOS = " \t\n\r\u000b\f\u00a0\u0085\ufeff";

function recortar(texto: string): string {
  let inicio = 0;
  let fin = texto.length;
  while (inicio < fin && BLANCOS.includes(texto[inicio]!)) inicio += 1;
  while (fin > inicio && BLANCOS.includes(texto[fin - 1]!)) fin -= 1;
  return texto.slice(inicio, fin);
}

export type LecturaDeCifra = { valor: string } | { error: string };

const CIFRA = /^(-?)([0-9]+|[1-9][0-9]{0,2}(?:\.[0-9]{3})+)(?:,([0-9]+))?$/;

// Lo escrito («1.234,5») al decimal con punto que espera la API («1234.5»), o el mensaje que se muestra junto al
// campo. Quien llama decide si un campo vacio vale cero o es un error.
export function leerCifra(texto: string): LecturaDeCifra {
  const limpio = recortar(texto);
  if (limpio === "") return { error: MENSAJE_CIFRA_VACIA };
  const m = CIFRA.exec(limpio);
  if (!m) return { error: MENSAJE_CIFRA };
  const [, signo, entera, decimales] = m;
  const digitos = entera!.replace(/\./g, "").replace(/^0+(?=[0-9])/, "");
  const esCero = /^0$/.test(digitos) && /^0*$/.test(decimales ?? "");
  return { valor: `${esCero ? "" : signo}${digitos}${decimales !== undefined ? `.${decimales}` : ""}` };
}

// El decimal de la API («1234.5», «3.000») como se escribe en un campo editable («1.234,5», «3,000»): vuelve igual al
// leerlo con `leerCifra`. Como `texto_de_cifra` del servidor: sin «+», sin ceros a la izquierda y sin cero negativo.
// Lo que no es un decimal se devuelve tal cual: un exponente («1E-7»), que la API debe evitar escribiendo sus
// decimales en notacion fija (`format(x, "f")`); si llega uno, queda en el campo y `leerCifra` lo rechaza.
export function textoParaEscribir(decimal: string): string {
  const m = DECIMAL.exec(decimal.trim());
  if (!m) return decimal;
  const [, signo, entera, decimales] = m;
  const canonica = entera!.replace(/^0+(?=[0-9])/, "");
  const fraccion = decimales === undefined ? "" : `.${decimales}`;
  const esCero = /^0$/.test(canonica) && /^0*$/.test(decimales ?? "");
  return formatoEsVe(`${signo === "-" && !esCero ? "-" : ""}${canonica}${fraccion}`);
}
