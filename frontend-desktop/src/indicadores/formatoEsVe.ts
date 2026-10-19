// Texto decimal de la API ("4358.20") a como se lee en es-VE ("4.358,20"): miles con punto, decimales con coma.
// Puro y sobre texto: nunca pasa por Number, asi un total de 30 cifras no pierde ninguna. Lo que no es un
// decimal se devuelve tal cual.
const DECIMAL = /^([-+]?)([0-9]+)(?:\.([0-9]+))?$/;

export function formatoEsVe(decimal: string): string {
  const m = DECIMAL.exec(decimal.trim());
  if (!m) return decimal;
  const [, signo, entera, fraccion] = m;
  const miles = entera.replace(/\B(?=([0-9]{3})+(?![0-9]))/g, ".");
  return `${signo}${miles}${fraccion !== undefined ? `,${fraccion}` : ""}`;
}

// Un monto con su unidad ("95066.60 USD") a es-VE ("95.066,60 USD"): se formatea el decimal inicial y lo que sigue
// (la unidad) queda igual. Lo que no empieza por un decimal (un porcentaje ya presentado, "no disponible") no se toca.
const MONTO = /^([-+]?[0-9]+(?:\.[0-9]+)?)(\s.*)?$/;

export function formatoMontoEsVe(texto: string): string {
  const m = MONTO.exec(texto.trim());
  if (!m) return texto;
  return `${formatoEsVe(m[1]!)}${m[2] ?? ""}`;
}
