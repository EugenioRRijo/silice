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

// Un total exacto de la API ("4876.56257") en centesimas y es-VE ("4.876,56"), para leerlo; el exacto va aparte (en el
// `title` o en un Tooltip). Solo cadena y BigInt, nunca float: redondeo «mitad hacia arriba» en valor absoluto, y un
// negativo que queda en cero se lee sin signo. Lo que no es un decimal se devuelve tal cual (VB-7).
export function centesimasEsVe(exacto: string): string {
  const m = DECIMAL.exec(exacto.trim());
  if (!m) return exacto;
  const [, signo, entera, fraccion = ""] = m;
  const centesimas = BigInt(entera + (fraccion + "00").slice(0, 2));
  const sube = fraccion.length > 2 && fraccion.charCodeAt(2) >= 53 ? 1n : 0n; // el tercer decimal es 5 o mas
  const total = (centesimas + sube).toString().padStart(3, "0");
  const texto = `${total.slice(0, -2)}.${total.slice(-2)}`;
  return formatoEsVe(signo === "-" && /[1-9]/.test(total) ? `-${texto}` : texto);
}

// Una fecha ISO de la API a como se lee en es-VE: «2026-11-02» -> «02/11/2026» y «2026-10-18T14:32:05» ->
// «18/10/2026 14:32». Lo que se envia a la API sigue siendo AAAA-MM-DD; esto es solo para leer (VB-19). Lo que no es
// una fecha ISO se devuelve tal cual.
export function fechaEsVe(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}))?/.exec(iso);
  if (!m) return iso;
  const dia = `${m[3]}/${m[2]}/${m[1]}`;
  return m[4] ? `${dia} ${m[4]}:${m[5]}` : dia;
}
