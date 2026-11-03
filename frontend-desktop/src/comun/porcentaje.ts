// La variacion llega de la API como fraccion decimal exacta ("0.0625"); se muestra en por ciento corriendo la
// coma dos lugares sobre el texto, sin pasar por float ni perder digitos (la interfaz no calcula montos).

const DECIMAL = /^([+-]?)(\d*)(?:\.(\d*))?(?:[eE]([+-]?\d+))?$/;

export function aPorcentaje(fraccion: string): string {
  const m = DECIMAL.exec(fraccion.trim());
  if (!m || (m[2] === "" && !m[3])) return fraccion;
  const signo = m[1] === "-" ? "-" : "";
  const exponente = Number(m[4] ?? "0") + 2;
  const digitos = (m[2] ?? "") + (m[3] ?? "");
  let coma = (m[2] ?? "").length + exponente;
  let todos = digitos;
  if (coma < 0) {
    todos = "0".repeat(-coma) + todos;
    coma = 0;
  } else if (coma > todos.length) {
    todos = todos + "0".repeat(coma - todos.length);
  }
  const entera = todos.slice(0, coma).replace(/^0+/, "") || "0";
  let decimal = todos.slice(coma);
  if (/^0*$/.test(decimal) && fraccion.trim().indexOf(".") === -1 && m[4] === undefined) decimal = "";
  else if (/^0*$/.test(decimal) && entera === "0") decimal = "";
  const cuerpo = decimal === "" ? entera : `${entera}.${decimal}`;
  return cuerpo === "0" ? "0" : signo + cuerpo;
}

export function fechaValida(texto: string): boolean {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(texto);
  if (!m) return false;
  const [a, mes, dia] = [Number(m[1]), Number(m[2]), Number(m[3])];
  const f = new Date(Date.UTC(a, mes - 1, dia));
  return f.getUTCFullYear() === a && f.getUTCMonth() === mes - 1 && f.getUTCDate() === dia;
}

export function rangoInvertido(desde: string, hasta: string): boolean {
  return fechaValida(desde) && fechaValida(hasta) && desde > hasta;
}
