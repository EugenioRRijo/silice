// Entregar paquete: la interfaz no calcula. Solo da formato al total exacto que manda la API, con operaciones de
// cadena y BigInt (nunca float): dos decimales (redondeo «mitad hacia arriba» en valor absoluto) y el formato es-VE
// del resto de la aplicacion (4.131,10). La regla vive en `centesimasEsVe`, la misma del Historial.
import { centesimasEsVe } from "../../indicadores/formatoEsVe";

export function totalPresentado(exacto: string): string {
  return centesimasEsVe(exacto);
}
