import { parsearA1 } from "../replica/coordenadas";
import type { CeldaRef } from "./hojaVisor";

// "HOJA!REF" (sin comillas ni $) -> { hoja, fila0, columna0 } en base 0. Separa por el ULTIMO "!" porque el
// nombre de una hoja puede tener signos de cierre de exclamacion. null si la referencia no es una celda A1
// ("APU-01!Rendimiento"), si falta la hoja o si viene vacia: esos hallazgos no se pueden marcar en la hoja.
export function parsearCelda(celda: string): CeldaRef | null {
  const corte = celda.lastIndexOf("!");
  if (corte <= 0) return null;
  const hoja = celda.slice(0, corte);
  const posicion = parsearA1(celda.slice(corte + 1));
  if (!posicion) return null;
  return { hoja, ...posicion };
}
