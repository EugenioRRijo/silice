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
