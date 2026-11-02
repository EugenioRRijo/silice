// Esbozo del rojo (Tarea 6 del plan F4): solo los tipos y las firmas, para que las pruebas fallen por lo que dicen.
import type { EstadoDeAprobacion } from "../../comun/aprobacion";
import type { VersionFila, VersionesRespuesta } from "../hoja/logica";

export interface FilaDeVersion extends VersionFila {
  estado: string | null;
  abierta: boolean;
}

export function filasDeVersiones(
  v: VersionesRespuesta,
  estados: Record<string, EstadoDeAprobacion> | null,
  abierta: string | null,
): FilaDeVersion[] {
  void [v, estados, abierta];
  return [];
}

export interface PasoDeVersiones {
  texto: string;
  accion: "guardar" | null;
}

export function pasoDeVersiones(e: { cambios: number; puedeGuardar: boolean; filas: FilaDeVersion[] }): PasoDeVersiones | null {
  void e;
  return null;
}
