// Iniciales de una persona para el círculo de la cuenta. Se parte el nombre por espacios (los sobrantes no cuentan) y de
// cada palabra se toma su primera letra o cifra. Una sola palabra da una inicial; con dos o más, la de la primera y la de
// la última, de modo que las partículas del medio («de la») no cuentan: «María José de la Fuente» da «MF». Sin letras
// (nombre vacío o de puros signos) da cadena vacía.
const PRIMERA = /[\p{L}\p{N}]/u;

export function iniciales(nombre: string): string {
  const letras = nombre
    .split(/\s+/)
    .map((palabra) => PRIMERA.exec(palabra)?.[0])
    .filter((letra): letra is string => letra !== undefined);
  if (letras.length === 0) return "";
  const elegidas = letras.length === 1 ? [letras[0]!] : [letras[0]!, letras[letras.length - 1]!];
  return elegidas.join("").toLocaleUpperCase("es");
}
