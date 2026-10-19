// Entregar paquete: la interfaz no calcula. Solo da formato al total exacto que manda la API, con operaciones de
// cadena y BigInt (nunca float): dos decimales (redondeo «mitad hacia arriba» en valor absoluto) y el formato es-VE
// del resto de la aplicacion (4.131,10).
import { formatoEsVe } from "../../indicadores/formatoEsVe";

const DECIMAL = /^([-+]?)([0-9]+)(?:\.([0-9]+))?$/;

export function totalPresentado(exacto: string): string {
  const m = DECIMAL.exec(exacto.trim());
  if (!m) return exacto;
  const [, signo, entera, fraccion = ""] = m;
  const centesimas = BigInt(entera + (fraccion + "00").slice(0, 2));
  const sube = fraccion.length > 2 && fraccion.charCodeAt(2) >= 53 ? 1n : 0n; // el tercer decimal es 5 o mas
  const total = (centesimas + sube).toString().padStart(3, "0");
  const texto = `${total.slice(0, -2)}.${total.slice(-2)}`;
  return formatoEsVe(signo === "-" && /[1-9]/.test(total) ? `-${texto}` : texto);
}
