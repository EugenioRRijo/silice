// Entregar paquete: la interfaz no calcula. Solo da formato al total exacto que manda la API, con operaciones de
// cadena y BigInt (nunca float): dos decimales y coma de miles, como el resto de la aplicacion.
import { formatearMostrado } from "../../replica/formatoNumero";

export function totalPresentado(exacto: string): string {
  const texto = formatearMostrado(exacto.trim(), "#,##0.00");
  return texto === "-0.00" ? "0.00" : texto;
}
