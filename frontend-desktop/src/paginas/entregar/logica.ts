// Entregar paquete: la interfaz no calcula. Solo da formato al total exacto que manda la API, con operaciones de
// cadena y BigInt (nunca float): dos decimales (redondeo «mitad hacia arriba» en valor absoluto) y el formato es-VE
// del resto de la aplicacion (4.131,10). La regla vive en `centesimasEsVe`, la misma del Historial.
import { centesimasEsVe } from "../../indicadores/formatoEsVe";

export function totalPresentado(exacto: string): string {
  return centesimasEsVe(exacto);
}

// Singular y plural de cada severidad, como se nombran en el resto de la interfaz (VB-16).
const NOMBRES: Record<string, [string, string]> = {
  CRITICO: ["crítico", "críticos"],
  ERROR: ["error", "errores"],
  ADVERTENCIA: ["advertencia", "advertencias"],
  INFO: ["informativo", "informativos"],
};

// Los hallazgos en una linea, en el orden que manda la API: «2 advertencias, 1 error». Una severidad en cero no se
// lista; una que la interfaz no conoce se nombra tal cual llega, en minusculas.
export function textoDeHallazgos(porSeveridad: Record<string, number>): string {
  return Object.entries(porSeveridad)
    .filter(([, n]) => n > 0)
    .map(([severidad, n]) => {
      const nombres = NOMBRES[severidad.toUpperCase()];
      const nombre = nombres ? nombres[n === 1 ? 0 : 1] : severidad.toLowerCase();
      return `${n} ${nombre}`;
    })
    .join(", ");
}
